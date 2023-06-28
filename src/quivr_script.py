import requests
from src import log
logger = log.setup_logger(__name__)
def get_token(login_url,login_email,login_password,apikey):
    # 登录获取JWT令牌
    login_data = {
        'email': login_email,
        'password': login_password,
        'gotrue_meta_security': {}
    }
    headers = {'apikey': f'{apikey}',
                'Authorization': f'Bearer {apikey}'
               }

    response = requests.post(login_url,headers=headers, json=login_data)
    # print(response.text)
    token = response.json()['access_token']
    return token

def quivr_chat(api_url,question,token):
    chat_url = api_url +"/chat"
    # 创建聊天消息
    chat_message = {"name":question}
    # 请求聊天接口
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.post(chat_url, headers=headers, json=chat_message)
    chat_id = response.json()['chat_id']

    return chat_id


def quivr_question(api_url,chat_id,question,token):
    chat_question_url = api_url + f"/chat/{chat_id}/question"
    # 创建聊天消息
    chat_message = {
        'question': question,
        "temperature": 0,
        "max_tokens": 1000,
        'model': 'gpt-3.5-turbo-0613'  # 你希望使用的模型名称
    }
    # 请求聊天接口
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.post(chat_question_url, headers=headers, json=chat_message)
    logger.info(f"chat_question_url:{chat_question_url} ,question: {question}, Response:{response}")

    # print(response.text)
    # 输出返回的历史记录
    assistant_text = response.json()['assistant']
    # Extract assistant value
    # print(assistant_text)
    return assistant_text

def quivr_tg_question(api_url,question,token):
    chat_question_url = api_url + f"/chat/5a5ec9bd-bfac-48f4-9f59-bddd0e43740a/question"
    # 创建聊天消息
    chat_message = {
        'question': question,
        "temperature": 0,
        "max_tokens": 1000,
        'model': 'gpt-3.5-turbo-0613'  # 你希望使用的模型名称
    }
    # 请求聊天接口
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.post(chat_question_url, headers=headers, json=chat_message)
    logger.info(f"chat_question_url:{chat_question_url} , Response:{response}")

    # print(response.text)
    # 输出返回的历史记录
    assistant_text = response.json()['assistant']
    # Extract assistant value
    # print(assistant_text)
    return assistant_text


def crawl_url(api_url,target_url,token):
    api_crawl_url = api_url + "/crawl/"
    # 创建聊天消息
    payload = {
        'url': target_url,
        'js': False,
        "depth": 1,
        "max_pages": 100,
        'max_time': 60
    }
    # 请求聊天接口
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.post(api_crawl_url, headers=headers, json=payload)
    if response.status_code == 200:
        return (response.json())
    else:
        return "Error: Something went wrong,please check!"

