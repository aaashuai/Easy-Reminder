# Easy WeChat Reminder

1. 简介  
   微信群聊提醒机器人

   依赖于[wechaty](https://github.com/wechaty/python-wechaty)，感谢！

2. 安装  

   1. 参考[这里](https://python-wechaty.readthedocs.io/zh_CN/latest/introduction/use-web-protocol/) 启动web协议服务
   2. 配置环境变量
      1. 配置机器人ID(可先通过一次对话获取)
      2. 配置TOKEN (与1中运行的WECHATY_TOKEN相同)
      3. 配置 WECHATY_PUPPET_SERVICE_ENDPOINT (1启动的链接)

3. 使用方式

   1. <all tasks> 展示当前生效中的任务
   2. <help,cmd>  查看该命令使用方法
   3. <remind,日期,提醒内容> 注册一个提醒事件
   4. <cancel,task_id>  取消一个提醒事件

4. todo

   1. 添加特殊任务名称, 比如 remind,每天上午9点,give me a poem; 给我一句诗
   2. 过滤非消息性质的消息, 比如: xxx邀请xxx进群
   3. 提取基类，继承后，通过@command来注册命令并执行