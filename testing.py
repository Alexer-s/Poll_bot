import itertools
import os
from telegram import Bot, ReplyKeyboardMarkup
from telegram.ext import Filters, MessageHandler, PollAnswerHandler, Updater
from dotenv import load_dotenv


load_dotenv()

token: str = os.getenv('TOKEN', 'token')
admin_id: str = os.getenv('ADMIN_ID', 'admin_id')

bot = Bot(token=token)
updater = Updater(token=token, use_context=True)

poll_data: dict = {}
answers: dict = {}
wrong_answers: dict = {}
next_question: dict = {}

first_button = ReplyKeyboardMarkup(
    [['Начать тестирование'],],
    resize_keyboard=True
)

bot.send_message(
    admin_id,
    text='Сервер запущен',
    reply_markup=first_button
)


def start(update, context):
    if poll_data.get(update.effective_user.id):
        button = ReplyKeyboardMarkup(
            [['Продолжить тестирование'],],
            resize_keyboard=True
        )
        return bot.send_message(
            update.effective_user.id,
            text='Продолжим тестирование?',
            reply_markup=button
        )
    button = ReplyKeyboardMarkup(
        [['Начать тестирование'],],
        resize_keyboard=True
    )
    return bot.send_message(
        update.effective_user.id,
        text='Привет, начнем тестирование?',
        reply_markup=button
    )


def generate_polls():
    with open('test.txt', 'r', encoding='utf-8') as file:
        test = file.read()
        for question in test.split('\n'):
            item = question.split('; ')
            yield {
                'question': item[0],
                'options': item[1:-1],
                'answer': int(item[-1])
            }


def poll(user_id, question, options, button_name):
    button = ReplyKeyboardMarkup(
        [[button_name],],
        resize_keyboard=True
    )
    bot.send_poll(
        user_id,
        question,
        options,
        is_anonymous=False,
        reply_markup=button
    )


def add_answer(user_id, result_answer):
    if answers.get(user_id):
        return answers[user_id].append(result_answer)
    else:
        answers[user_id] = []
        return answers[user_id].append(result_answer)


def add_wrong_answer(user_id, question, answer):
    answer_str = f'На вопрос: {question} дан неправильный ответ: {answer}'
    if wrong_answers.get(user_id):
        return wrong_answers[user_id].append(answer_str)
    else:
        wrong_answers[user_id] = []
        return wrong_answers[user_id].append(answer_str)


def result_message(user_id):
    winning_message = 'Отлично! Все ответы правильные!'
    error_message = (
        'Тестирование закончено. Есть ошибки! '
        'Следует повторить темы с ошибочными ответами.'
    )
    button = ReplyKeyboardMarkup(
        [['Начать тестирование'],],
        resize_keyboard=True
    )
    if False not in answers[user_id]:
        bot.send_message(
            user_id,
            text=winning_message,
            reply_markup=button
        )
    else:
        bot.send_message(
            user_id,
            text=error_message,
            reply_markup=button
        )


def reporting_message(update):
    if False not in answers[update.effective_user.id]:
        result = 'Все ответы правильные.'
    else:
        result = 'Есть ошибки.'
    result_specialist = (
        f'Специалист: {update.effective_user.first_name}\n'
        f'Юзернейм: {update.effective_user.username}\n'
        f'Прошел тестирование с результатом: {result}'
    )
    if result == 'Есть ошибки.':
        result_specialist = result_specialist + '\n' + '\n'.join(
            wrong_answers[update.effective_user.id]
        )
    poll_data[update.effective_user.id] = 'stop'
    return bot.send_message(
        admin_id,
        text=result_specialist
    )


def receive_poll(update, context):
    if update.effective_user.id != int(admin_id):
        return bot.send_message(
            update.effective_user.id,
            text='Отсутствуют права администратора!'
        )
    poll_data.clear()
    try:
        poll_document_id = update.message.document.file_id
        download_poll_file = context.bot.get_file(poll_document_id)
        poll_file_bytearray = download_poll_file.download_as_bytearray()
        poll_file_text = poll_file_bytearray.decode('utf-8')
        poll_file_cleaned = '\n'.join(
            [line for line in poll_file_text.splitlines() if line.strip()]
        )
        with open('test.txt', 'w', encoding='utf-8') as file:
            file.write(poll_file_cleaned)
    except Exception as error:
        return bot.send_message(
            update.effective_user.id,
            text=f'При выполнении загрузки файла возникла ошибка: {error}'
        )
    return bot.send_message(
        update.effective_user.id,
        text='Тест успешно загружен!'
    )


def clear_poll(update, context):
    if update.effective_user.id == int(admin_id):
        poll_data.clear()
        answers.clear()
        wrong_answers.clear()
        next_question.clear()
        button = ReplyKeyboardMarkup(
            [['Начать тестирование'],],
            resize_keyboard=True
        )
        bot.send_message(
            update.effective_user.id,
            text='Тест сброшен!',
            reply_markup=button
        )
    else:
        bot.send_message(
            update.effective_user.id,
            text='Нет прав!'
        )


def income(update, context):
    if poll_data.get(update.effective_user.id):
        if poll_data[update.effective_user.id] == 'stop':
            return bot.send_message(
                update.effective_user.id,
                text='Вы уже прошли этот тест!'
            )
        poll_generators = poll_data[update.effective_user.id]
    elif update.message and update.message.text == 'Начать тестирование':
        next_question[update.effective_user.id] = False
        poll_generator = generate_polls()
        poll_generators = itertools.tee(poll_generator, 2)
        poll_data[update.effective_user.id] = poll_generators

    if update.poll_answer:
        next_question[update.effective_user.id] = True
        prev_item = next(poll_generators[1])
        if update.poll_answer.option_ids[0] + 1 == prev_item['answer']:
            add_answer(
                update.effective_user.id,
                True
            )
            return bot.send_message(
                update.effective_user.id,
                text='Это правильный ответ!'
            )
        else:
            add_answer(
                update.effective_user.id,
                False
            )
            add_wrong_answer(
                update.effective_user.id,
                prev_item['question'],
                prev_item['options'][update.poll_answer.option_ids[0]]
            )
            return bot.send_message(
                update.effective_user.id,
                text=(
                    'Не правильно! Правильный ответ: '
                    f'{prev_item["options"][prev_item["answer"] - 1]}'
                )
            )
    if (
        update.message
        and update.message.text in (
            'Начать тестирование',
            'Продолжить тестирование'
        )
        and next_question.get(update.effective_user.id) is not None
        and (
            next_question[update.effective_user.id] is True
            or (
                next_question[update.effective_user.id] is False
                and update.message.text == 'Начать тестирование'
            )
        )
    ):
        button = 'Продолжить тестирование'
        try:
            question_data = next(poll_generators[0])
        except StopIteration:
            result_message(update.effective_user.id)
            reporting_message(update)
            return bot.send_message(
                update.effective_user.id,
                text='Опрос закончен!'
            )
        poll(
            update.effective_user.id,
            question_data['question'],
            question_data['options'],
            button
        )
        next_question[update.effective_user.id] = False
    else:
        bot.send_message(
            update.effective_user.id,
            text='Нужно выбрать вариант ответа!'
        )

updater.dispatcher.add_handler(MessageHandler(
    Filters.text & Filters.regex('Начать тестирование'),
    income)
)
updater.dispatcher.add_handler(MessageHandler(
    Filters.text & Filters.regex('Продолжить тестирование'),
    income)
)
updater.dispatcher.add_handler(MessageHandler(
    Filters.text & Filters.regex('Сбросить тест'),
    clear_poll)
)
updater.dispatcher.add_handler(MessageHandler(Filters.text, start))
updater.dispatcher.add_handler(MessageHandler(Filters.document, receive_poll))
updater.dispatcher.add_handler(PollAnswerHandler(income))
updater.start_polling()
updater.idle()
