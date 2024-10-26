import itertools
import os
from telegram import Bot
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


def generate_polls():
    with open('test.txt', 'r', encoding='utf-8') as file:
        test = file.read()
        for question in test.split('\n'):
            yield {
                'question': question.split('; ')[0],
                'options': question.split('; ')[1:-1],
                'answer': int(question.split('; ')[-1])
            }


def poll(user_id, question, options):
    bot.send_poll(
        user_id,
        question,
        options,
        is_anonymous=False
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
        'Есть ошибки! Следует повторить темы с ошибочными ответами.'
    )
    if False not in answers[user_id]:
        bot.send_message(
            user_id,
            text=winning_message
        )
    else:
        bot.send_message(
            user_id,
            text=error_message
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


def income(update, context):
    if poll_data.get(update.effective_user.id):
        if poll_data[update.effective_user.id] == 'stop':
            return bot.send_message(
                update.effective_user.id,
                text='Вы уже прошли этот тест!'
            )
        poll_generators = poll_data[update.effective_user.id]
    else:
        poll_generator = generate_polls()
        poll_generators = itertools.tee(poll_generator, 2)
        poll_data[update.effective_user.id] = poll_generators
    if update.poll_answer:
        prev_item = next(poll_generators[1])
        if update.poll_answer.option_ids[0] + 1 == prev_item['answer']:
            add_answer(
                update.effective_user.id,
                True
            )
            bot.send_message(
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
            bot.send_message(
                update.effective_user.id,
                text=(
                    'Не правильно! Правильный ответ: '
                    f'{prev_item["options"][prev_item["answer"] - 1]}'
                )
            )
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
        question_data['options']
    )


updater.dispatcher.add_handler(MessageHandler(Filters.text, income))
updater.dispatcher.add_handler(MessageHandler(Filters.document, receive_poll))
updater.dispatcher.add_handler(PollAnswerHandler(income))
updater.start_polling()
updater.idle()