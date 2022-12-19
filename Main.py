import json
import os
from hashlib import md5
from datetime import datetime, date
from datetime import timedelta
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import requests
from requests.adapters import HTTPAdapter


requests.adapters.DEFAULT_RETRIES = 10
pwd = os.path.dirname(os.path.abspath(__file__)) + os.sep

s = requests.session()
s.mount('http://', HTTPAdapter(max_retries=10))
s.mount('https://', HTTPAdapter(max_retries=10))
s.keep_alive = False

headers = {
    "os": "ios",
    "phone": "iPhone12",
    "appVersion": "39",
    "Sign": "Sign",
    "cl_ip": "192.168.1.2",
    "User-Agent": "okhttp/3.14.9",
    "Content-Type": "application/json;charset=utf-8"
}


def getMd5(text: str):
    return md5(text.encode('utf-8')).hexdigest()

def get_date(days):
    # 格式化为 年月日 形式 2019-02-25
    return (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")

def parseUserInfo():
    allUser = ''
    if os.path.exists(pwd + "user.json"):
        print('读取配置文件')
        with open(pwd + "user.json", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines:
                allUser = allUser + line + '\n'
    else:
        return json.loads(os.environ.get("USERS", ""))
    return json.loads(allUser)
 
def sendEmail(user,nr):
    # 创建 SMTP 对象
    smtp = smtplib.SMTP()
    # 连接（connect）指定服务器
    smtp.connect("smtp.qq.com", port=25)
    # 登录，需要：登录邮箱和授权码
    smtp.login(user="1173877142@qq.com", password="akkkzlqyaeopggci")
    message = MIMEText(nr, 'plain', 'utf-8')
    message['From'] = Header("职校家园", 'utf-8')
    message['To'] =  Header(user["alias"], 'utf-8')
    subject = '职校家园'
    message['Subject'] = Header(subject, 'utf-8')
    smtp.sendmail(from_addr="1173877142@qq.com", to_addrs=user["email"], msg=message.as_string())

def save(user, uid, token):
    url = 'http://sxbaapp.zcj.jyt.henan.gov.cn/interface/clockindaily.ashx'

    data = {
        "dtype": 1,
        "uid": uid,
        "address": user["address"],
        "phonetype": user["deviceType"],
    }
    headers["Sign"] = getMd5(json.dumps(data) + token)
    res = requests.post(url, headers=headers, data=json.dumps(data))

    if res.json()["code"] == 1001:
        return True, res.json()["msg"]
    return False, res.json()["msg"]


def getToken():
    url = 'http://sxbaapp.zcj.jyt.henan.gov.cn/interface/token.ashx'
    res = requests.post(url, headers=headers)
    if res.json()["code"] == 1001:
        return True, res.json()["data"]["token"]
    return False, res.json()["msg"]


def login(user, token):
    password = getMd5(user["password"])
    deviceId = user["deviceId"]

    data = {
        "phone": user["phone"],
        "password": password,
        "dtype": 6,
        "dToken": deviceId
    }
    headers["Sign"] = getMd5((json.dumps(data) + token))
    url = 'http://sxbaapp.zcj.jyt.henan.gov.cn/interface/relog.ashx'
    res = requests.post(url, headers=headers, data=json.dumps(data))
    return res.json()

def report(data):
    res,token=getToken()
    headers["Sign"] = getMd5((json.dumps(data) + token))
    url = 'http://sxbaapp.zcj.jyt.henan.gov.cn/interface/ReportHandler.ashx'
    res = requests.post(url, headers=headers, data=json.dumps(data))
    return res.json()

def autoReport(user,uid):
    #获取系统时间
    now=datetime.now()
    #转化接口需要的日期,yyyy-MM-dd
    nowStr=now.strftime("%Y-%m-%d")
    #获取当天是几号，写月报用
    dayStr=now.strftime("%d")
    #获取当天是周几,写周报用
    weekDayStr=now.weekday()
    weekRes=''
    monthRes=''
    # 日报
    # 实习项目:project
    # 实习记录:record
    # 实习总结:summary
    data1 = {
        "address" : user['comaddress'],
        "uid" : uid,
        "summary" : user['summary1'],
        "record" : user['record1'],
        "starttime" : nowStr,
        "dtype" : 1,
        "project" : user['project1']
    }
    # 提交日报
    dayRes=str(report(data1)) 
    # 周报
    if weekDayStr == 6:
        weekstime=get_date(6)
        data2 = {
            "address" : user['comaddress'],
            "uid" : uid,
            "starttime" : weekstime,
            "record" : user['record2'],
            "summary" : user['summary2'],
            "dtype" : 2,
            "project" : user['project2'],
            "stype" : 2,
            "endtime" : nowStr
        }
        # 提交周报
        weekRes=str(report(data2))
    
    
    #月报
    if dayStr == 30:
        monthstime=get_date(29)
        data3 = {
            "address" : user['comaddress'],
            "uid" : uid,
            "starttime" : monthstime,
            "record" : user['record3'],
            "summary" : user['summary3'],
            "dtype" : 2,
            "project" : user['project3'],
            "stype" : 3,
            "endtime" : nowStr
        }
        # 提交月报
        monthRes=str(report(data3))
    return dayRes+weekRes+monthRes

def prepareSign(user):
    if not user["enable"]:
        print(user['alias'], '未启用打卡，即将跳过')
        return

    print('已加载用户', user['alias'], '即将开始打卡')

    headers["phone"] = user["deviceType"]

    res, token = getToken()
    if not res:
        print('用户', user['alias'], '获取Token失败')
        return

    loginResp = login(user, token)

    if loginResp["code"] != 1001:
        print('用户', user['alias'], '登录账号失败，错误原因：', loginResp["msg"])
        return

    uid = loginResp["data"]["uid"]
    print(uid)
    resp, msg = save(user, uid, token)
    msg2=autoReport(user,uid)
    print("返回结果:",msg2)
    if resp:
        print(user["alias"], '打卡成功！')
        sendEmail(user,"职校家园提交结果:"+msg)
        return
    print(user["alias"], "打卡失败!失败原因:",msg)
    sendEmail(user,"打卡，日报失败!失败原因:"+msg)


if __name__ == '__main__':
    users = parseUserInfo()
    for user in users:
        try:
            prepareSign(user)
        except Exception as e:
            print('职校家园打卡失败，错误原因：' + str(e))