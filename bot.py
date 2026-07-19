import asyncio
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ENGINEER_ID_RAW = os.getenv("ENGINEER_ID", "").strip()
ENGINEER_ID = int(ENGINEER_ID_RAW) if ENGINEER_ID_RAW else None
DB_PATH = Path(os.getenv("DB_PATH", "robo_stock.db"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден")


def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def now_text():
    return datetime.now().isoformat(timespec="seconds")


def init_db():
    con = connection()
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS shifts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        operator_name TEXT NOT NULL,
        station INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT,
        is_active INTEGER NOT NULL DEFAULT 1)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS frames(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shift_id INTEGER NOT NULL,
        station INTEGER NOT NULL,
        frame_number INTEGER NOT NULL,
        current_position INTEGER NOT NULL DEFAULT 1,
        start_time TEXT NOT NULL,
        finish_time TEXT,
        is_active INTEGER NOT NULL DEFAULT 1)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS stops(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shift_id INTEGER NOT NULL,
        frame_id INTEGER NOT NULL,
        station INTEGER NOT NULL,
        robot TEXT,
        error_name TEXT,
        stop_time TEXT NOT NULL,
        launch_time TEXT,
        downtime_seconds INTEGER,
        is_active INTEGER NOT NULL DEFAULT 1)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS transitions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shift_id INTEGER NOT NULL,
        frame_id INTEGER NOT NULL,
        station INTEGER NOT NULL,
        from_position INTEGER NOT NULL,
        to_position INTEGER,
        finish_time TEXT NOT NULL,
        launch_time TEXT,
        seconds INTEGER,
        is_active INTEGER NOT NULL DEFAULT 1)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS consumables(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shift_id INTEGER NOT NULL,
        frame_id INTEGER NOT NULL,
        station INTEGER NOT NULL,
        robot TEXT NOT NULL,
        consumable TEXT NOT NULL,
        replacement_time TEXT NOT NULL)""")
    con.commit(); con.close()


def one(query, args=()):
    con=connection(); cur=con.cursor(); cur.execute(query,args); row=cur.fetchone(); con.close(); return row


def all_rows(query,args=()):
    con=connection(); cur=con.cursor(); cur.execute(query,args); rows=cur.fetchall(); con.close(); return rows


def execute(query,args=()):
    con=connection(); cur=con.cursor(); cur.execute(query,args); rid=cur.lastrowid; con.commit(); con.close(); return rid


def active_shift(uid):
    return one("SELECT * FROM shifts WHERE user_id=? AND is_active=1 ORDER BY id DESC LIMIT 1",(uid,))


def active_frame(shift_id):
    return one("SELECT * FROM frames WHERE shift_id=? AND is_active=1 ORDER BY id DESC LIMIT 1",(shift_id,))


def active_stop(shift_id):
    return one("SELECT * FROM stops WHERE shift_id=? AND is_active=1 ORDER BY id DESC LIMIT 1",(shift_id,))


def active_transition(frame_id):
    return one("SELECT * FROM transitions WHERE frame_id=? AND is_active=1 ORDER BY id DESC LIMIT 1",(frame_id,))


def fmt_time(value):
    return datetime.fromisoformat(value).strftime("%H:%M:%S")


def fmt_duration(seconds):
    seconds=max(0,int(seconds)); h,rem=divmod(seconds,3600); m,s=divmod(rem,60)
    if h: return f"{h} ч {m} мин {s} сек"
    if m: return f"{m} мин {s} сек"
    return f"{s} сек"


def keyboard(rows):
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=x) for x in row] for row in rows],resize_keyboard=True)

START=keyboard([["▶ Начать смену"]])
STATIONS=keyboard([["🏭 Станция 1"],["🏭 Станция 2"],["🏭 Станция 3"]])
MAIN=keyboard([["⛔ Остановка"],["🔄 Следующее положение"],["🔧 Расходники"],["📊 Статистика смены"],["🏁 Завершить смену"]])
ROBOTS=keyboard([["R1","R3","R2"]])
ERRORS=keyboard([["🔍 Ошибка поиска"],["💨 Нет газа"],["🧵 Нет проволоки"],["🚨 Аварийный стоп"],["🤖 Столкновение"],["⚙ Другая ошибка"]])
LAUNCH=keyboard([["▶ Запуск станции"]])
FINISH_FRAME=keyboard([["🏁 Завершить раму"]])
NEW_FRAME=keyboard([["▶ Начать новую раму"],["🏁 Завершить смену"]])
CONSUMABLES=keyboard([["Наконечник"],["Сопло"],["Контактная трубка"],["Проволока"],["Спрей антипригарный"]])
CONFIRM=keyboard([["✅ Да, завершить смену"],["↩ Нет, вернуться"]])

class S(StatesGroup):
    station=State(); stop_robot=State(); error=State(); launch=State(); next_launch=State(); finish_frame=State(); new_frame=State(); cons_robot=State(); cons=State(); finish_shift=State()

router=Router()
ERR_MAP={"🔍 Ошибка поиска":"Ошибка поиска","💨 Нет газа":"Нет газа","🧵 Нет проволоки":"Нет проволоки","🚨 Аварийный стоп":"Аварийный стоп","🤖 Столкновение":"Столкновение","⚙ Другая ошибка":"Другая ошибка"}
ST_MAP={"🏭 Станция 1":1,"🏭 Станция 2":2,"🏭 Станция 3":3}

async def notify(bot,text):
    if ENGINEER_ID is None: return
    try: await bot.send_message(ENGINEER_ID,text)
    except Exception: logging.exception("Ошибка уведомления инженеру")

@router.message(CommandStart())
async def start(m:Message,state:FSMContext):
    await state.clear(); sh=active_shift(m.from_user.id)
    if sh:
        await m.answer(f"🏭 У вас уже идёт смена.\n\nСтанция: {sh['station']}",reply_markup=MAIN); return
    await m.answer("🏭 Электронный журнал роботизированного участка\n\nНажмите кнопку, чтобы начать работу.",reply_markup=START)

@router.message(Command("id"))
async def show_id(m:Message): await m.answer(f"Ваш Telegram ID:\n{m.from_user.id}")

@router.message(F.text=="▶ Начать смену")
async def begin(m:Message,state:FSMContext):
    await state.set_state(S.station); await m.answer("Выберите станцию:",reply_markup=STATIONS)

@router.message(S.station,F.text.in_(ST_MAP.keys()))
async def choose_station(m:Message,state:FSMContext):
    station=ST_MAP[m.text]; name=(m.from_user.full_name or m.from_user.username or str(m.from_user.id))
    sid=execute("INSERT INTO shifts(user_id,operator_name,station,start_time,is_active) VALUES(?,?,?,?,1)",(m.from_user.id,name,station,now_text()))
    fid=execute("INSERT INTO frames(shift_id,station,frame_number,current_position,start_time,is_active) VALUES(?,?,1,1,?,1)",(sid,station,now_text()))
    await state.clear(); await m.answer(f"✅ Смена начата\n\nСтанция: {station}\nРама: №1\nТекущее положение: 1",reply_markup=MAIN)

@router.message(F.text=="⛔ Остановка")
async def stop(m:Message,state:FSMContext):
    sh=active_shift(m.from_user.id); fr=active_frame(sh['id']) if sh else None
    if not sh or not fr: await m.answer("Активная смена или рама не найдена."); return
    if active_transition(fr['id']): await m.answer("Сначала запустите следующее положение."); return
    sid=execute("INSERT INTO stops(shift_id,frame_id,station,stop_time,is_active) VALUES(?,?,?,?,1)",(sh['id'],fr['id'],sh['station'],now_text()))
    await state.update_data(stop_id=sid); await state.set_state(S.stop_robot)
    await m.answer(f"🔴 Остановка зафиксирована\n\nСтанция: {sh['station']}\nРама: №{fr['frame_number']}\nВремя: {fmt_time(active_stop(sh['id'])['stop_time'])}\n\nВыберите робот:",reply_markup=ROBOTS)

@router.message(S.stop_robot,F.text.in_({"R1","R2","R3"}))
async def choose_robot(m:Message,state:FSMContext):
    data=await state.get_data(); execute("UPDATE stops SET robot=? WHERE id=?",(m.text,data['stop_id']))
    await state.set_state(S.error); await m.answer("Выберите ошибку:",reply_markup=ERRORS)

@router.message(S.error,F.text.in_(ERR_MAP.keys()))
async def choose_error(m:Message,state:FSMContext):
    data=await state.get_data(); error=ERR_MAP[m.text]; execute("UPDATE stops SET error_name=? WHERE id=?",(error,data['stop_id']))
    sh=active_shift(m.from_user.id); fr=active_frame(sh['id']); st=active_stop(sh['id'])
    await notify(m.bot,f"🔴 Остановка станции\n\n🏭 Станция: {sh['station']}\n🏗 Рама: №{fr['frame_number']}\n📍 Положение: {fr['current_position']}\n🤖 Робот: {st['robot']}\n⚠ Ошибка: {error}\n🕒 Время: {fmt_time(st['stop_time'])}\n👤 Оператор: {sh['operator_name']}")
    await state.set_state(S.launch); await m.answer(f"✅ Ошибка записана\n\nОшибка: {error}",reply_markup=LAUNCH)

@router.message(S.launch,F.text=="▶ Запуск станции")
async def launch(m:Message,state:FSMContext):
    sh=active_shift(m.from_user.id); st=active_stop(sh['id']); launch_time=datetime.now(); seconds=int((launch_time-datetime.fromisoformat(st['stop_time'])).total_seconds())
    execute("UPDATE stops SET launch_time=?,downtime_seconds=?,is_active=0 WHERE id=?",(launch_time.isoformat(timespec='seconds'),seconds,st['id']))
    done=one("SELECT * FROM stops WHERE id=?",(st['id'],)); fr=active_frame(sh['id'])
    await notify(m.bot,f"🟢 Станция снова запущена\n\n🏭 Станция: {sh['station']}\n🏗 Рама: №{fr['frame_number']}\n📍 Положение: {fr['current_position']}\n🤖 Робот: {done['robot']}\n⚠ Ошибка: {done['error_name']}\n⌛ Простой: {fmt_duration(seconds)}")
    await state.clear(); await m.answer(f"🟢 Станция запущена\n\nРобот: {done['robot']}\nОшибка: {done['error_name']}\nВремя простоя: {fmt_duration(seconds)}",reply_markup=MAIN)

@router.message(F.text=="🔄 Следующее положение")
async def next_position(m:Message,state:FSMContext):
    sh=active_shift(m.from_user.id); fr=active_frame(sh['id']) if sh else None
    if not fr: await m.answer("Активная рама не найдена."); return
    p=fr['current_position']
    if p==4:
        await state.set_state(S.finish_frame); await m.answer("✅ Положение 4 завершено",reply_markup=FINISH_FRAME); return
    tr=active_transition(fr['id'])
    if not tr: execute("INSERT INTO transitions(shift_id,frame_id,station,from_position,finish_time,is_active) VALUES(?,?,?,?,?,1)",(sh['id'],fr['id'],sh['station'],p,now_text()))
    await state.set_state(S.next_launch); await m.answer(f"✅ Положение {p} завершено\n\nВыполните чистку.",reply_markup=keyboard([[f"▶ Запуск положения {p+1}"]]))

@router.message(S.next_launch,F.text.startswith("▶ Запуск положения "))
async def launch_position(m:Message,state:FSMContext):
    sh=active_shift(m.from_user.id); fr=active_frame(sh['id']); tr=active_transition(fr['id']); launch=datetime.now(); sec=int((launch-datetime.fromisoformat(tr['finish_time'])).total_seconds()); n=tr['from_position']+1
    execute("UPDATE transitions SET to_position=?,launch_time=?,seconds=?,is_active=0 WHERE id=?",(n,launch.isoformat(timespec='seconds'),sec,tr['id']))
    execute("UPDATE frames SET current_position=? WHERE id=?",(n,fr['id']))
    await state.clear(); await m.answer(f"▶ Положение {n} запущено\n\nВремя чистки: {fmt_duration(sec)}",reply_markup=MAIN)

@router.message(S.finish_frame,F.text=="🏁 Завершить раму")
async def finish_frame(m:Message,state:FSMContext):
    sh=active_shift(m.from_user.id); fr=active_frame(sh['id']); finish=now_text(); execute("UPDATE frames SET finish_time=?,is_active=0 WHERE id=?",(finish,fr['id']))
    stops=all_rows("SELECT * FROM stops WHERE frame_id=? AND is_active=0",(fr['id'],)); trans=all_rows("SELECT * FROM transitions WHERE frame_id=? AND is_active=0",(fr['id'],)); cons=all_rows("SELECT * FROM consumables WHERE frame_id=?",(fr['id'],))
    dur=int((datetime.fromisoformat(finish)-datetime.fromisoformat(fr['start_time'])).total_seconds()); down=sum(int(x['downtime_seconds'] or 0) for x in stops); clean=sum(int(x['seconds'] or 0) for x in trans)
    await state.set_state(S.new_frame); await m.answer(f"🏁 Рама №{fr['frame_number']} завершена\n\nОбщее время: {fmt_duration(dur)}\n⛔ Остановок: {len(stops)}\nОбщий простой: {fmt_duration(down)}\n🔄 Чисток: {len(trans)}\nВремя чистки: {fmt_duration(clean)}\n🔧 Расходников: {len(cons)}",reply_markup=NEW_FRAME)

@router.message(S.new_frame,F.text=="▶ Начать новую раму")
async def new_frame(m:Message,state:FSMContext):
    sh=active_shift(m.from_user.id); count=one("SELECT COUNT(*) AS n FROM frames WHERE shift_id=?",(sh['id'],))['n']+1
    execute("INSERT INTO frames(shift_id,station,frame_number,current_position,start_time,is_active) VALUES(?,?,?,1,?,1)",(sh['id'],sh['station'],count,now_text()))
    await state.clear(); await m.answer(f"✅ Новая рама начата\n\nРама: №{count}\nПоложение: 1",reply_markup=MAIN)

@router.message(F.text=="🔧 Расходники")
async def consumables(m:Message,state:FSMContext): await state.set_state(S.cons_robot); await m.answer("Выберите робот:",reply_markup=ROBOTS)

@router.message(S.cons_robot,F.text.in_({"R1","R2","R3"}))
async def cons_robot(m:Message,state:FSMContext): await state.update_data(robot=m.text); await state.set_state(S.cons); await m.answer("Выберите расходник:",reply_markup=CONSUMABLES)

@router.message(S.cons)
async def save_cons(m:Message,state:FSMContext):
    sh=active_shift(m.from_user.id); fr=active_frame(sh['id']); data=await state.get_data(); execute("INSERT INTO consumables(shift_id,frame_id,station,robot,consumable,replacement_time) VALUES(?,?,?,?,?,?)",(sh['id'],fr['id'],sh['station'],data['robot'],m.text,now_text())); await state.clear(); await m.answer("✅ Замена записана",reply_markup=MAIN)


def statistics(shift_id):
    frames=one("SELECT COUNT(*) AS n FROM frames WHERE shift_id=? AND is_active=0",(shift_id,))['n']; st=one("SELECT COUNT(*) AS n,COALESCE(SUM(downtime_seconds),0) AS s FROM stops WHERE shift_id=? AND is_active=0",(shift_id,)); tr=one("SELECT COUNT(*) AS n,COALESCE(AVG(seconds),0) AS a FROM transitions WHERE shift_id=? AND is_active=0",(shift_id,)); cons=one("SELECT COUNT(*) AS n FROM consumables WHERE shift_id=?",(shift_id,))['n']; return frames,st,tr,cons

@router.message(F.text=="📊 Статистика смены")
async def stats(m:Message):
    sh=active_shift(m.from_user.id); fr=active_frame(sh['id']); frames,st,tr,cons=statistics(sh['id']); elapsed=int((datetime.now()-datetime.fromisoformat(sh['start_time'])).total_seconds()); available=max(0,elapsed-st['s'])/elapsed*100 if elapsed else 100
    await m.answer(f"📊 Статистика смены\n\n👤 Оператор: {sh['operator_name']}\n🏭 Станция: {sh['station']}\n⏱ Прошло: {fmt_duration(elapsed)}\n\nТекущая рама: №{fr['frame_number'] if fr else '—'}\nПоложение: {fr['current_position'] if fr else '—'}\nГотовых рам: {frames}\n\n⛔ Остановок: {st['n']}\n⌛ Простой: {fmt_duration(st['s'])}\n🔄 Чисток: {tr['n']}\nСредняя чистка: {fmt_duration(tr['a'])}\n🔧 Расходников: {cons}\n\n📈 Доступность: {available:.1f}%",reply_markup=MAIN)

@router.message(F.text=="🏁 Завершить смену")
async def ask_finish(m:Message,state:FSMContext):
    sh=active_shift(m.from_user.id); fr=active_frame(sh['id']) if sh else None
    if fr: await m.answer("Сначала завершите раму.",reply_markup=MAIN); return
    await state.set_state(S.finish_shift); await m.answer("❓ Завершить смену?",reply_markup=CONFIRM)

@router.message(S.finish_shift,F.text=="↩ Нет, вернуться")
async def no_finish(m:Message,state:FSMContext): await state.clear(); await m.answer("Отменено",reply_markup=MAIN)

@router.message(S.finish_shift,F.text=="✅ Да, завершить смену")
async def yes_finish(m:Message,state:FSMContext):
    sh=active_shift(m.from_user.id); frames,st,tr,cons=statistics(sh['id']); end=now_text(); execute("UPDATE shifts SET end_time=?,is_active=0 WHERE id=?",(end,sh['id'])); dur=int((datetime.fromisoformat(end)-datetime.fromisoformat(sh['start_time'])).total_seconds()); available=max(0,dur-st['s'])/dur*100 if dur else 100
    await state.clear(); await m.answer(f"🏁 Смена завершена\n\n👤 Оператор: {sh['operator_name']}\n🏭 Станция: {sh['station']}\n⏱ Продолжительность: {fmt_duration(dur)}\n\n🏗 Готовых рам: {frames}\n⛔ Остановок: {st['n']}\n⌛ Простой: {fmt_duration(st['s'])}\n🔄 Чисток: {tr['n']}\n🔧 Расходников: {cons}\n📈 Доступность: {available:.1f}%",reply_markup=START)

async def main():
    logging.basicConfig(level=logging.INFO); init_db(); bot=Bot(BOT_TOKEN); dp=Dispatcher(); dp.include_router(router); print("Бот запущен"); await dp.start_polling(bot)

if __name__=="__main__": asyncio.run(main())
