#!/usr/bin/env python  
# _#_ coding:utf-8 _*_ 
import os
from celery import task
from OpsManage.utils import base
from OpsManage.models import (Log_Assets,Log_Ansible_Model,Project_Order,
                              Log_Ansible_Playbook,Log_Cron_Config,
                              Log_Project_Config,Global_Config,Email_Config,
                              Ansible_Script,Ansible_Playbook,Server_Assets,
                              Ansible_Playbook_Number)
from OpsManage.data.DsMySQL import AnsibleRecord
from OpsManage.utils.ansible_api_v2 import ANSRunner
from django.contrib.auth.models import User
'''
Django 版本大于等于1.7的时候，需要加上下面两句
import django
django.setup()
否则会抛出错误 django.core.exceptions.AppRegistryNotReady: Models aren't loaded yet.
'''
 
import django
if django.VERSION >= (1, 7):#自动判断版本
    django.setup()
    

@task  
def recordAssets(user,content,type,id=None):
    try:
        config = Global_Config.objects.get(id=1)
        if config.assets == 1:
            logs = Log_Assets.objects.create(
                                      assets_id = id,
                                      assets_user = user,
                                      assets_content = content,
                                      assets_type = type
                                      )
        return logs.id
    except Exception,e:
        print e
        return False

@task  
def recordAnsibleModel(user,ans_model,ans_server,uuid,ans_args=None):
    try:
        config = Global_Config.objects.get(id=1)
        if config.ansible_model == 1:
            Log_Ansible_Model.objects.create(
                                      ans_user = user,
                                      ans_server = ans_server,
                                      ans_args = ans_args,
                                      ans_model = ans_model,
                                      ans_uuid = uuid
                                      )
            return True
    except Exception,e:
        return False
    
@task  
def recordAnsiblePlaybook(user,ans_id,ans_name,ans_content,uuid=None,ans_server=None):
    try:
        config = Global_Config.objects.get(id=1)
        if config.ansible_playbook == 1:
            Log_Ansible_Playbook.objects.create(
                                      ans_user = user,
                                      ans_server = ans_server,
                                      ans_name = ans_name,
                                      ans_id = ans_id,
                                      ans_content = ans_content,
                                      ans_uuid = uuid
                                      )
        return True
    except Exception,e:
        print e
        return False
    
@task  
def recordCron(cron_user,cron_id,cron_name,cron_content,cron_server=None):
    try:
        config = Global_Config.objects.get(id=1)
        if config.cron == 1:
            Log_Cron_Config.objects.create(
                                      cron_id = cron_id,
                                      cron_user = cron_user,
                                      cron_name = cron_name,
                                      cron_content = cron_content,
                                      cron_server = cron_server
                                      )
        return True
    except Exception,e:
        print e
        return False

@task  
def recordProject(project_user,project_id,project_name,project_content,project_branch=None):
    try:
        config = Global_Config.objects.get(id=1)
        if config.project == 1:
            Log_Project_Config.objects.create(
                                      project_id = project_id,
                                      project_user = project_user,
                                      project_name = project_name,
                                      project_content = project_content,
                                      project_branch = project_branch
                                      )
        return True
    except Exception,e:
        print e
        return False
    
@task  
def sendEmail(order_id,mask):
    try:
        config = Email_Config.objects.get(id=1)
        order = Project_Order.objects.get(id=order_id)
    except:
        return False
    content = """申请人：{user}<br>                                          
                                         更新内容：{content}<br>
                                        工单地址：<a href='{site}/deploy_order/status/{order_id}/'>点击查看工单</a><br>
                                        授权人：{auth}<br>""".format(order_id=order_id,user=order.order_user,
                                           site=config.site,auth=order.order_audit,
                                           content=order.order_content)
    if order.order_cancel:
        content += "撤销原因：<strong>{order_cancel}</strong>".format(order_cancel=order.order_cancel)
    to_user = User.objects.get(username=order.order_audit).email
    if config.subject:subject = "{sub} {oub} {mask}".format(sub=config.subject,oub=order.order_subject,mask=mask)
    else:subject = "{oub} {mask}".format(mask=mask,oub=order.order_subject)
    if config.cc_user:
        cc_to = config.cc_user
    else:cc_to = None
    base.sendEmail(e_from=config.user,e_to=to_user,cc_to=cc_to,
                   e_host=config.host,e_passwd=config.passwd,
                   e_sub=subject,e_content=content)
    return True

@task  
def AnsibleScripts(**kw):
    logId = None
    resource = []
    try:
        if kw.has_key('scripts_id'):
            script = Ansible_Script.objects.get(id=kw.get('scripts_id'))
            filePath = os.getcwd()  + str(script.script_file)
            if kw.has_key('hosts'):
                try:
                    sList = list(kw.get('hosts'))
                except Exception, ex:
                    return ex
            else:
                try:
                    sList = list(script.script_server)
                except Exception, ex:
                    return ex           
            if kw.has_key('logs'):
                logId = AnsibleRecord.Model.insert(user='celery',ans_model='script',ans_server=','.join(sList),ans_args=filePath)
            for sip in sList:
                try:
                    server_assets = Server_Assets.objects.get(ip=sip)
                except Exception, ex:
                    continue
                if server_assets.keyfile == 1:resource.append({"hostname": server_assets.ip, "port": int(server_assets.port)})
                else:resource.append({"hostname": server_assets.ip, "port": int(server_assets.port),"username": server_assets.username,"password": server_assets.passwd})         
            ANS = ANSRunner(resource,redisKey=None,logId=logId)
            ANS.run_model(host_list=sList,module_name='script',module_args=filePath)
            return ANS.get_model_result()
    except Exception,e:
        print e
        return False
    
    
@task  
def AnsiblePlayBook(**kw):
    logId = None
    resource = []
    try:
        if kw.has_key('playbook_id'):
            playbook = Ansible_Playbook.objects.get(id=kw.get('playbook_id'))
            filePath = os.getcwd()  + str(playbook.playbook_file)
            if kw.has_key('hosts'):
                try:
                    sList = list(kw.get('hosts'))
                except Exception, ex:
                    return ex
            else:
                try:
                    numberList = Ansible_Playbook_Number.objects.filter(playbook=playbook)
                    if numberList:sList = [ s.playbook_server for s in numberList ]
                except Exception, ex:
                    return ex           
            if kw.has_key('logs'):
                logId = AnsibleRecord.PlayBook.insert(user='celery',ans_id=playbook.id,ans_name=playbook.playbook_name,
                                            ans_content=u"执行Ansible剧本",ans_server=','.join(sList)) 
            for sip in sList:
                try:
                    server_assets = Server_Assets.objects.get(ip=sip)
                except Exception, ex:
                    continue
                if server_assets.keyfile == 1:resource.append({"hostname": server_assets.ip, "port": int(server_assets.port)})
                else:resource.append({"hostname": server_assets.ip, "port": int(server_assets.port),"username": server_assets.username,"password": server_assets.passwd})         
            ANS = ANSRunner(resource,redisKey=None,logId=logId)
            ANS.run_playbook(host_list=sList, playbook_path=filePath)
            return ANS.get_playbook_result()
    except Exception,e:
        print e
        return False