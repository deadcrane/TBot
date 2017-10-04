#!/usr/bin/env python
# coding: utf-8
import ConfigParser

from wxbot import *
import datetime
import urllib2


def handle_msg_chat(bot, msg):  # 处理单个聊天
    msg_content = msg['content']['data']
    segs = msg_content.split(u'\u2005')
    if len(segs) <= 1:
        segs = msg_content.split(u'\u0020')
    # 注册新用户
    if segs[0] == u'注册':
        submit_user_to_app_server(bot, msg, segs[1], segs[2])
    else:
        bot.send_msg_by_uid('如需连接t.ikongleng.com，只需回复【注册 用户名 密码】即可，如【注册 jinhefeng 666666】。',
                            msg['user']['id'])


def handle_msg_group(bot, msg, isatme):  # 处理群消息
    if isatme:  # 判断是否为@消息
        src_name = msg['content']['user']['name']
        reply = '@' + src_name + u'\u2005'
        if msg['content']['type'] == 0:  # text message
            reply += u"不理你~~"
        else:
            reply += u"对不起，只认字，其他杂七杂八的我都不认识，,,Ծ‸Ծ,,"
        bot.send_msg_by_uid(reply, msg['user']['id'])
    else:
        return


def submit_user_to_app_server(bot, msg, username, password):
    data = {'username': username, 'password': password}
    req = urllib2.Request(
        url='http://'+bot.APP_SERVER+'/submit_user_to_TBot/',
        data=urllib.urlencode(data)
    )
    res = urllib2.urlopen(req)
    # 提交 username和password到appserver，检查是否能够登陆,若可以则反馈用户姓名
    submit_result = res.read()
    if not submit_result.isdigit():
        remark_name = bot.APP_SERVER + "#" + submit_result
        uid = bot.get_user_id(remark_name)
        if uid:
            uname = bot.get_contact_name(uid)['nickname']
            bot.set_remarkname(uid, uname.encode("utf-8"))  # 注销别人的备注名称
        bot.set_remarkname(msg['user']['id'], remark_name)  # 修改用户的备注名称
        bot.send_msg_by_uid('恭喜，注册成功！', msg['user']['id'])
        bot.get_contact()
    else:
        bot.send_msg_by_uid('注册失败，请重新检查用户名和密码！', msg['user']['id'])
    return


# ——————————————————————自动任务处理器——————————————————————————————————————


def check_now_is_work_time():
    today = datetime.date.today()
    now = datetime.datetime.now()
    start_time_str = (today.strftime('%Y-%m-%d') + ' 08:00:00')
    end_time_str = (today.strftime('%Y-%m-%d') + ' 21:30:00')
    start_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    end_time = datetime.datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
    if start_time < now < end_time:
        flag = True
    else:
        flag = False
        print 'NO'
    return flag


class Task:
    def __init__(self, nbot, start_time, freq):
        self.bot = nbot
        self.freq = freq
        self.start_time = start_time
        self.method = ''

    def handle_task(self):
        pass

    def do(self):
        if check_now_is_work_time():    # 检查是否为工作时间
            now = datetime.datetime.now()
            print now.strftime("%Y-%m-%d %H:%M:%S") + '@' + self.method
            if (now - self.start_time).seconds > self.freq:
                self.start_time = self.start_time + datetime.timedelta(seconds=self.freq)
                while (now - self.start_time).seconds > self.freq:
                    self.start_time = self.start_time + datetime.timedelta(seconds=self.freq)
                self.handle_task()


def get_json_from_app_server(app_server, method):
    url = 'http://' + app_server + '/' + method
    req = urllib2.Request(url=url, )
    res = urllib2.urlopen(req)
    notice_json = json.loads(res.read())
    return notice_json


class RealTimeNotifyTask(Task):
    def __init__(self, nbot, start_time, freq):
        Task.__init__(self, nbot, start_time, freq)
        self.method = 'get_all_tbot_notify'

    def handle_task(self):
        self.method = 'get_all_tbot_notify'
        notice_json = get_json_from_app_server(self.bot.APP_SERVER, self.method)
        if notice_json['notice']:
            for notice in notice_json['notice']:
                if notice['name'] == 'group':
                    touser = self.bot.GROUP_NAME
                else:
                    touser = self.bot.APP_SERVER + "#" + notice['name'].__str__()
                self.bot.send_msg(touser, notice['content'])
        print 'method:' + notice_json['method'].__str__() + '@OK'


class GenUnConfirmTask(Task):
    def __init__(self, nbot, start_time, freq):
        Task.__init__(self, nbot, start_time, freq)
        self.method = 'gen_unconfirm_task_notify'

    def handle_task(self):
        notice_json = get_json_from_app_server(self.bot.APP_SERVER, self.method)
        print 'method:' + notice_json['method'].__str__() + '@' + notice_json['notice'].__str__()


class GenDailyWorkLoad(Task):
    def __init__(self, nbot, start_time, freq):
        Task.__init__(self, nbot, start_time, freq)
        self.method = 'gen_day_work_load_notify'

    def handle_task(self):
        notice_json = get_json_from_app_server(self.bot.APP_SERVER, self.method)
        print 'method:' + notice_json['method'].__str__() + '@' + notice_json['notice'].__str__()


# ——————————————————————初始化机器人
class MyTBot(WXBot):
    def __init__(self):
        WXBot.__init__(self)
        self.robot_switch = True
        self.task_list = []
        try:
            cf = ConfigParser.ConfigParser()
            cf.read('conf.ini')
            self.APP_SERVER = cf.get('main', 'APP_SERVER')  # 网站地址
            self.GROUP_NAME = cf.get('main', 'GROUP_NAME')  # 群名称
            self.VERIFY_CODE = cf.get('main', 'VERIFY_CODE')  # 加好友验证码
            print "APP_SERVER:" + self.APP_SERVER + '\n'
            print "GROUP_NAME:" + self.GROUP_NAME + '\n'
            print "VERIFY_CODE:" + self.VERIFY_CODE + '\n'
        except Exception:
            print 'config file read error'
            pass
        print 'TBot is Running...'

    def handle_msg_all(self, msg):
        if not self.robot_switch and msg['msg_type_id'] != 1:
            return
        if msg['msg_type_id'] == 37:    # 添加好友
            if msg['content']['data']['Content'] == self.VERIFY_CODE:    # 验证码为Amber
                self.apply_useradd_requests(msg['content']['data'])
        if (msg['msg_type_id'] == 4 or msg['msg_type_id'] == 99) and msg['content']['type'] == 0:  # text message from contact
            handle_msg_chat(self, msg)
        elif msg['msg_type_id'] == 3 and msg['content']['type'] == 0:  # group text message
            if 'detail' in msg['content']:
                my_names = self.get_group_member_name(msg['user']['id'], self.my_account['UserName'])
                if my_names is None:
                    my_names = {}
                if 'NickName' in self.my_account and self.my_account['NickName']:
                    my_names['nickname2'] = self.my_account['NickName']
                if 'RemarkName' in self.my_account and self.my_account['RemarkName']:
                    my_names['remark_name2'] = self.my_account['RemarkName']

                is_at_me = False
                for detail in msg['content']['detail']:
                    if detail['type'] == 'at':
                        for k in my_names:
                            if my_names[k] and my_names[k] == detail['value']:
                                is_at_me = True
                                break
                handle_msg_group(self, msg, is_at_me)

    def schedule(self):
        for task in self.task_list:
            task.do()
        time.sleep(1)


def main():
    bot = MyTBot()
    bot.DEBUG = False
    bot.conf['qr'] = 'png'
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    get_notice_task = RealTimeNotifyTask(bot, datetime.datetime.now(), 10)  # 获取未读消息的任务，频率10s
    gen_un_confirm_task = GenUnConfirmTask(bot, datetime.datetime.strptime((today_str + " 09:30:00"), "%Y-%m-%d %H:%M:%S"),
                                           3600)  # 获取未签审的任务汇总，频率每小时
    gen_daily_work_load = GenDailyWorkLoad(bot, datetime.datetime.strptime((yesterday_str + " 10:00:00"), "%Y-%m-%d %H:%M:%S"),
                                           3600 * 24)  # 获取每个工作量统计，频率每天
    bot.task_list.append(get_notice_task)
    bot.task_list.append(gen_daily_work_load)
    bot.task_list.append(gen_un_confirm_task)
    bot.run()


if __name__ == '__main__':
    main()
