# Easy WeChat Reminder

## 1. 简介  
   微信群聊提醒机器人


## 2. 安装  

   1. 参考[这里](https://python-wechaty.readthedocs.io/zh_CN/latest/introduction/use-web-protocol/) 启动web协议服务
   2. 配置环境变量
      1. 配置TOKEN (与1中运行的WECHATY_TOKEN相同)
      2. 配置 WECHATY_PUPPET_SERVICE_ENDPOINT (1启动的链接)

## 3. 使用方式

   1. <\all tasks> 展示当前生效中的任务
   2. <\help,cmd>  查看该命令使用方法
   3. <\remind,日期,提醒内容> 注册一个提醒事件
   4. <\cancel,task_id>  取消一个提醒事件

## Thanks

[![PyCharm](https://github.com/dongweiming/lyanna/raw/master/docs/pycharm.svg)](https://www.jetbrains.com/?from=easy_wechaty_reminder)
<a href="https://wechaty.js.org/"><img src="https://camo.githubusercontent.com/8663c7fa27f9849e4002ca4d8f4b032c420e0ecce53757c2f6c1859a250561ee/68747470733a2f2f776563686174792e6a732e6f72672f696d672f776563686174792d6c6f676f2e737667" width="455px" height="128px" alt="wechaty" /></a>
