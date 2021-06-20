# easy_wechat_reminder

1. 简介  
   微信群聊提醒机器人
2. 安装  
    在.env中
    1. 配置机器人ID(可先通过一次对话获取)
    2. 配置TOKEN
    3. 配置 WECHATY_PUPPET_SERVICE_ENDPOINT
3. 使用方式  [todo: 将基本框架提取出来，用户可以通过@command来注册命令并执行]
    1. <all tasks> 展示当前生效中的任务
    2. <help,cmd>  查看该命令使用方法
    3. <remind,日期,提醒内容> 注册一个提醒事件
    4. <cancel,task_id>  取消一个提醒事件
    
4. todo
    1. 添加特殊任务名称, 比如 remind,每天上午9点,give me a poem; 给我一句诗