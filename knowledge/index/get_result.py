# -*- coding: utf-8 -*-

import json
import csv
import os
import time
import math
from datetime import date
from datetime import datetime
from elasticsearch.helpers import scan
import knowledge.model
from knowledge.model import *
from knowledge.extensions import db
from knowledge.global_config import *
from knowledge.global_utils import *
from knowledge.global_utils import R_RECOMMENTATION as r,ES_CLUSTER_FLOW1 as es_cluster
from knowledge.parameter import DAY
from knowledge.time_utils import ts2datetime, datetime2ts

org_list = [1,2,3,4,5,6,7,8]

def uid_name(uid_list,result):

    search_result = es_user_portrait.mget(index=portrait_index_name, doc_type=portrait_index_type, body={"ids": uid_list})["docs"]
    if len(search_result) == 0:
        return result
    for item in search_result:
        uid = item['_id']
        if not item['found']:
            result[uid]['name'] = ''
            continue
        else:
            data = item['_source']
            try:
                result[uid]['name'] = data['uname'].encode('utf-8')
            except:
                result[uid]['name'] = ''

    return result

def uid_name_list(uid_list):

    search_result = es_user_portrait.mget(index=portrait_index_name, doc_type=portrait_index_type, body={"ids": uid_list})["docs"]
    if len(search_result) == 0:
        return '-1'
    uname = dict()
    for item in search_result:
        uid = item['_id']
        if not item['found']:
            uname[uid] = ''
            continue
        else:
            data = item['_source']
            try:
                uname[uid] = data['uname'].encode('utf-8')
            except:
                uname[uid] = ''

    return uname

def eventid_name(uidlist):

    search_result = es_event.mget(index=event_analysis_name, doc_type=event_text_type, body={"ids": uidlist})["docs"]
    if len(search_result) == 0:
        return result
    for item in search_result:
        uid = item['_id']
        if not item['found']:
            result[uid]['name'] = ''
            continue
        else:
            data = item['_source']
            try:
                result[uid]['name'] = data['name'].encode('utf-8')
            except:
                result[uid]['name'] = ''

    return result
            
def get_people(name,count):#获取我关注的人物

    infors = db.session.query(PeopleAttention).filter(PeopleAttention.name==name).all()
    result = dict()
    uid_list = []
    if count == 'all':#获取所有数据
        for infor in infors:
            uid = infor.peopleID
            uid_list.append(uid)
            result[uid] = {'label':infor.label,'time':infor.attentionTime,'name':''}
    else:
        n = 0
        for infor in infors:
            n = n + 1
            if n > count:
                break
            uid = infor.peopleID
            uid_list.append(uid)
            result[uid] = {'label':infor.label,'time':infor.attentionTime,'name':''}

    if len(uid_list) > 0:
        result = uid_name(uid_list,result)
    
    return result.values()

def get_event(name,count):#获取我关注的事件

    infors = db.session.query(EventAttention).filter(EventAttention.name==name).all()
    result = dict()
    uid_list = []
    if count == 'all':#获取所有数据
        for infor in infors:
            uid = infor.eventID
            uid_list.append(uid)
            result[uid] = {'label':infor.label,'time':infor.attentionTime,'name':''}
    else:
        n = 0
        for infor in infors:
            n = n + 1
            if n > count:
                break
            uid = infor.eventID
            uid_list.append(uid)
            result[uid] = {'label':infor.label,'time':infor.attentionTime,'name':''}

    if len(uid_list) > 0:
        result = eventid_name(uid_list,result)
    
    return result.values()

def get_org(name,count):#获取我关注的机构

    infors = db.session.query(OrgAttention).filter(OrgAttention.name==name).all()
    result = dict()
    uid_list = []
    if count == 'all':#获取所有数据
        for infor in infors:
            uid = infor.orgID
            uid_list.append(uid)
            result[uid] = {'label':infor.label,'time':infor.attentionTime,'name':''}
    else:
        n = 0
        for infor in infors:
            n = n + 1
            if n > count:
                break
            uid = infor.orgID
            uid_list.append(uid)
            result[uid] = {'label':infor.label,'time':infor.attentionTime,'name':''}

    if len(uid_list) > 0:
        result = uid_name(uid_list,result)
    
    return result.values()

def get_hot_weibo():#获取热门微博
    
    end_ts = time.time()
    start_ts = 1479312000#2016-11-17  end_ts-24*3600        
        
    query_body = {
        "query":{
            "bool":{
                "must":[{'range':{'detect_ts':{'gt':start_ts,'lt':end_ts}}}],
            }
        },
        "size":2
    }
    search_results = es_social_sensing_text.search(index=social_sensing_index_name, doc_type=social_sensing_index_type, body=query_body)['hits']['hits']
    n = len(search_results)
    result = []
    uid_list = []
    if n > 0:
        for item in search_results:
            mid = item['_id'].encode('utf-8')
            data = item['_source']
            text = data['text'].encode('utf-8')
            uid = data['uid'].encode('utf-8')
            uid_list.append(uid)
            ts = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(float(data['timestamp'])))
            result.append({'mid':mid,'text':text,'uid':uid,'time':ts})

    if len(result) > 0:
        uname_dict = uid_name_list(uid_list)

    if uname_dict == '-1':
        new_result = []
        for item in result:
            uid = item['uid']
            item['uname'] = ''
            new_result.append(item)
    else:
        new_result = []
        for item in result:
            uid = item['uid']
            item['uname'] = uname_dict[uid]
            new_result.append(item)
        
    return new_result    

# show recommentation in uid
def recommentation_in(input_ts, recomment_type):
    date = ts2datetime(input_ts)
    recomment_results = []
    results = []
    hash_name = 'recomment_'+str(date) + "_" + recomment_type
    identify_in_hashname = "identify_in_" + str(date)
    results = r.hgetall(hash_name)
    if not results:
        return []
    recommend_list = set(r.hkeys(hash_name))
    identify_in_list = set(r.hkeys("compute"))
    recomment_results = list(recommend_list - identify_in_list)[0:3]

    if recomment_results:
        results = get_user_detail(date, recomment_results)
    else:
        results = []
    return results

def get_evaluate_max(index_name):
    max_result = {}
    index_type = 'bci'
    evaluate_index = ['user_index']
    for evaluate in evaluate_index:
        query_body = {
            'query':{
                'match_all':{}
                },
            'size':1,
            'sort':[{evaluate: {'order': 'desc'}}]
            }
        result = es_cluster.search(index=index_name, doc_type=index_type, body=query_body)['hits']['hits']
        max_evaluate = result[0]['_source'][evaluate]
        max_result[evaluate] = max_evaluate
    return max_result

#get user detail
#output: uid, uname, location, fansnum, statusnum, influence
def get_user_detail(date, input_result):
    bci_date = ts2datetime(datetime2ts(date) - DAY)
    results = []
    uid_list = input_result
    if date!='all':
        index_name = 'bci_' + ''.join(bci_date.split('-'))
    else:
        now_ts = time.time()
        now_date = ts2datetime(now_ts)
        index_name = 'bci_' + ''.join(now_date.split('-'))
    index_type = 'bci'
    user_bci_result = es_cluster.mget(index=index_name, doc_type=index_type, body={'ids':uid_list}, _source=True)['docs']  #INFLUENCE,fans,status
    user_profile_result = es_user_profile.mget(index=profile_index_name, doc_type=profile_index_type, body={'ids':uid_list}, _source=True)['docs'] #个人姓名，注册地
    max_evaluate_influ = get_evaluate_max(index_name)
    for i in range(0, len(uid_list)):
        uid = uid_list[i]
        bci_dict = user_bci_result[i]
        profile_dict = user_profile_result[i]

        try:
            bci_source = bci_dict['_source']
        except:
            bci_source = None
        if bci_source:
            influence = bci_source['user_index']
            influence = math.log(influence/float(max_evaluate_influ['user_index']) * 9 + 1 ,10)
            influence = influence * 100
        else:
            influence = ''
        try:
            profile_source = profile_dict['_source']
        except:
            profile_source = None
        if profile_source:
            uname = profile_source['nick_name'] 
            location = profile_source['user_location']
            try:
                fansnum = bci_dict['fields']['user_fansnum'][0]
            except:
                fansnum = 0
            try:
                statusnum = bci_dict['fields']['weibo_month_sum'][0]
            except:
                statusnum = 0
        else:
            uname = uid
            location = ''
            try:
                fansnum = bci_dict['fields']['user_fansnum'][0]
            except:
                fansnum = 0
            try:
                statusnum = bci_dict['fields']['weibo_month_sum'][0]
            except:
                statusnum = 0

        results.append({'uid':uid, 'uname':uname, 'location':location, 'fansnum':fansnum, 'statusnum':statusnum, 'influence':influence})

    return results

def get_hot_people():#获取热门人物

    input_ts = 1480176000#time.time()
    results = recommentation_in(input_ts, 'influence')
    return results

def get_map_count():#获取地图统计

    location_result = dict()
    no_location_count = 0
    s_re = scan(es_user_portrait, query={'query':{'match_all':{}}}, index=portrait_index_name, doc_type=portrait_index_type)
    while True:
        try:
            scan_re = s_re.next()['_source']
            try:
                location = scan_re['location']
                if not location:
                    no_location_count += 1
                    continue
                if len(location.split(' '))>1:
                    location = location.split(' ')[0]
                try:
                    location_result[location] += 1
                except:
                    location_result[location] = 1
            except:
                no_location_count += 1
        except StopIteration:
            print 'ALL done'
            break

    return location_result
    

def get_geo():#获取事件地址

    event_result = dict()
    no_location_count = 0
    s_re = scan(es_event, query={'query':{'match_all':{}}}, index=event_analysis_name, doc_type=event_text_type)
    count = 0
    while True:
        count = count + 1
        if count > 20:
            break
        try:
            scan_re = s_re.next()['_source']
            try:
                location = eval(scan_re['geo_results'])
                name = scan_re['name'].encode('utf-8')
                event_result[name] = location
            except:
                no_location_count += 1
        except StopIteration:
            print 'ALL done'
            break

    people_result = dict()
    org_result = dict()
    s_re = scan(es_user_portrait, query={'query':{'match_all':{}}}, index=portrait_index_name, doc_type=portrait_index_type)
    count = 0
    while True:
        count = count + 1
        if count > 100:
            break
        try:
            scan_re = s_re.next()['_source']
            try:
                location = scan_re['location'].encode('utf-8')
                name = scan_re['uname'].encode('utf-8')
                if not location:
                    no_location_count += 1
                    continue
                if not name:
                    name = scan_re['uid']
                if len(location.split(' '))>1:
                    location = location.split(' ')[0]
                if scan_re['verified_type'] in org_list:
                    org_result[name] = location
                else:
                    people_result[name] = location
            except:
                no_location_count += 1
        except StopIteration:
            print 'ALL done'
            break
    
    return event_result,people_result,org_result

def get_type_key(item):
    if item == 1:#人物
        return people_primary
    elif item == 2:#事件
        return event_primary
    elif item == 0:#机构
        return org_primary
    elif item == 3:#专题
        return special_event_primary
    elif item == 4:#群体
        return group_primary
    else:
        return 'Not Found'

def get_detail_person(uid_list):

    if len(uid_list) == 0:
        return {}
    result = {}
    search_result = es_user_portrait.mget(index=portrait_index_name, doc_type=portrait_index_type, body={"ids": uid_list})["docs"]
    if len(search_result) == 0:
        return result
    for item in search_result:
        uid = item['_id']
        if not item['found']:
            result[uid] = {}
            continue
        else:
            data = item['_source']
            if not data['uname']:
                name = ''
            else:
                name = data['uname'].encode('utf-8')
            domain = data['domain'].encode('utf-8')
            if not data['location']:
                location = ''
            else:
                location = data['location'].encode('utf-8')           
            if not data['verified_type']:
                verified = ''
            else:
                verified = ver_data[data['verified_type']]
            importance = data['importance']
            influence = data['influence']
            activeness = data['activeness']

            #还差粉丝数、业务标签
            result[uid] = {'name':name,'domain':domain,'importance':importance,'influence':influence,'activeness':activeness,'location':location,'verified':verified}

    return result

def get_detail_org(uid_list):

    if len(uid_list) == 0:
        return {}
    result = {}
    search_result = es_user_portrait.mget(index=portrait_index_name, doc_type=portrait_index_type, body={"ids": uid_list})["docs"]
    if len(search_result) == 0:
        return result
    for item in search_result:
        uid = item['_id']
        if not item['found']:
            result[uid] = {}
            continue
        else:
            data = item['_source']
            if not data['uname']:
                name = ''
            else:
                name = data['uname'].encode('utf-8')

            if not data['location']:
                location = ''
            else:
                location = data['location'].encode('utf-8')           
            if not data['verified_type']:
                verified = ''
            else:
                verified = ver_data[data['verified_type']]

            #还差粉丝数、业务标签
            result[uid] = {'name':name,'location':location,'verified':verified}

    return result

def get_detail_event(uid_list):

    if len(uid_list) == 0:
        return {}
    search_result = es_event.mget(index=event_analysis_name, doc_type=event_text_type, body={"ids": uidlist})["docs"]
    if len(search_result) == 0:
        return result
    for item in search_result:
        uid = item['_id']
        if not item['found']:
            result[uid] = {}
            continue
        else:
            data = item['_source']
            if not data['name']:
                name = ''
            else:
                name = data['name'].encode('utf-8')
            if data['real_geo'] != 'NULL':
                geo = data['real_geo'].encode('utf-8')
            else:
                geo = ''
            category = data['category']
            if data['real_time'] != 'NULL':
                time_ts = data['real_time'].encode('utf-8')
            else:
                time_ts = ''

            #还差业务标签
            result[uid] = {'name':name,'geo':geo,'category':category,'time_ts':time_ts}

    return result

def get_relation_node(user_id,node_type,card_type):#获取关联节点

    node_key = get_type_key(node_type)
    card_key = get_type_key(card_type)
    if node_key == 'Not Found' or card_key == 'Not Found':#未找到匹配类型
        return [],-1
    if node_key == people_primary:
        if card_key == people_primary:#uid-uid
            start_index_name = node_index_name
            end_index_name = node_index_name
            c_string = 'START n=node:%s("%s:*"),m=node:%s("%s:*") MATCH (n)-[r]-(m) return m.%s LIMIT 100' % (start_index_name,node_key,end_index_name,card_key,card_key)
            p_result = graph.run(c_string)
            uid_list = []
            for item in p_result:
                uid_list.append(item[0])
            result = get_detail_person(uid_list)#获取用户详细信息
            flag = 1
        elif card_key == event_primary:#uid-event
            start_index_name = node_index_name
            end_index_name = event_index_name
            c_string = 'START n=node:%s("%s:*"),m=node:%s("%s:*") MATCH (n)-[r]-(m) return m.%s LIMIT 100' % (start_index_name,node_key,end_index_name,card_key,card_key)
            p_result = graph.run(c_string)
            uid_list = []
            for item in p_result:
                uid_list.append(item[0])
            result = get_detail_event(uid_list)#获取事件详细信息
            flag = 2
        else:#uid-org
            start_index_name = node_index_name
            end_index_name = org_index_name
            c_string = 'START n=node:%s("%s:*"),m=node:%s("%s:*") MATCH (n)-[r]-(m) return m.%s LIMIT 100' % (start_index_name,node_key,end_index_name,card_key,card_key)
            p_result = graph.run(c_string)
            uid_list = []
            for item in p_result:
                uid_list.append(item[0])
            result = get_detail_org(uid_list)#获取用户详细信息
            flag = 0

    elif node_key == event_primary:
        if card_key == people_primary:#event-uid
            start_index_name = event_index_name
            end_index_name = node_index_name
            c_string = 'START n=node:%s("%s:*"),m=node:%s("%s:*") MATCH (n)-[r]-(m) return m.%s LIMIT 100' % (start_index_name,node_key,end_index_name,card_key,card_key)
            p_result = graph.run(c_string)
            uid_list = []
            for item in p_result:
                uid_list.append(item[0])
            result = get_detail_person(uid_list)#获取用户详细信息
            flag = 1
        elif card_key == event_primary:#event-event
            start_index_name = event_index_name
            end_index_name = event_index_name
            c_string = 'START n=node:%s("%s:*"),m=node:%s("%s:*") MATCH (n)-[r]-(m) return m.%s LIMIT 100' % (start_index_name,node_key,end_index_name,card_key,card_key)
            p_result = graph.run(c_string)
            uid_list = []
            for item in p_result:
                uid_list.append(item[0])
            result = get_detail_event(uid_list)#获取用户详细信息
            flag = 2
        else:#event-org
            start_index_name = event_index_name
            end_index_name = org_index_name
            c_string = 'START n=node:%s("%s:*"),m=node:%s("%s:*") MATCH (n)-[r]-(m) return m.%s LIMIT 100' % (start_index_name,node_key,end_index_name,card_key,card_key)
            p_result = graph.run(c_string)
            uid_list = []
            for item in p_result:
                uid_list.append(item[0])
            result = get_detail_org(uid_list)#获取用户详细信息
            flag = 0

    elif node_key == org_primary:
        if card_key == people_primary:#org-uid
            start_index_name = org_index_name
            end_index_name = node_index_name
            c_string = 'START n=node:%s("%s:*"),m=node:%s("%s:*") MATCH (n)-[r]-(m) return m.%s LIMIT 100' % (start_index_name,node_key,end_index_name,card_key,card_key)
            p_result = graph.run(c_string)
            uid_list = []
            for item in p_result:
                uid_list.append(item[0])
            result = get_detail_person(uid_list)#获取用户详细信息
            flag = 1
        elif card_key == event_primary:#org-event
            start_index_name = org_index_name
            end_index_name = event_index_name
            c_string = 'START n=node:%s("%s:*"),m=node:%s("%s:*") MATCH (n)-[r]-(m) return m.%s LIMIT 100' % (start_index_name,node_key,end_index_name,card_key,card_key)
            p_result = graph.run(c_string)
            uid_list = []
            for item in p_result:
                uid_list.append(item[0])
            result = get_detail_event(uid_list)#获取用户详细信息
            flag = 2
        else:#org-org
            start_index_name = org_index_name
            end_index_name = org_index_name
            c_string = 'START n=node:%s("%s:*"),m=node:%s("%s:*") MATCH (n)-[r]-(m) return m.%s LIMIT 100' % (start_index_name,node_key,end_index_name,card_key,card_key)
            p_result = graph.run(c_string)
            uid_list = []
            for item in p_result:
                uid_list.append(item[0])
            result = get_detail_org(uid_list)#获取用户详细信息
            flag = 0

    elif node_key == special_event_primary:
        if card_key == people_primary:#special_event-uid
            start_index_name = node_index_name
            end_index_name = node_index_name
            c_string = 'START n=node:%s("%s:*"),m=node:%s("%s:*") MATCH (n)-[]-()-[]-(m) return m.%s LIMIT 100' % (start_index_name,node_key,end_index_name,card_key,card_key)
            p_result = graph.run(c_string)
            uid_list = []
            for item in p_result:
                uid_list.append(item[0])
            result = get_detail_person(uid_list)#获取用户详细信息
            flag = 1
        elif card_key == event_primary:#special_event-event
            start_index_name = node_index_name
            end_index_name = event_index_name
            c_string = 'START n=node:%s("%s:*"),m=node:%s("%s:*") MATCH (n)-[]-()-[]-(m) return m.%s LIMIT 100' % (start_index_name,node_key,end_index_name,card_key,card_key)
            p_result = graph.run(c_string)
            uid_list = []
            for item in p_result:
                uid_list.append(item[0])
            result = get_detail_person(uid_list)#获取用户详细信息
            flag = 2
        else:#special_event-org
            start_index_name = node_index_name
            end_index_name = org_index_name
            c_string = 'START n=node:%s("%s:*"),m=node:%s("%s:*") MATCH (n)-[]-()-[]-(m) return m.%s LIMIT 100' % (start_index_name,node_key,end_index_name,card_key,card_key)
            p_result = graph.run(c_string)
            uid_list = []
            for item in p_result:
                uid_list.append(item[0])
            result = get_detail_org(uid_list)#获取用户详细信息
            flag = 0

    else:
        if card_key == people_primary:#group-uid
            start_index_name = group_index_name
            end_index_name = node_index_name
            c_string = 'START n=node:%s("%s:*"),m=node:%s("%s:*") MATCH (n)-[]-()-[]-(m) return m.%s LIMIT 100' % (start_index_name,node_key,end_index_name,card_key,card_key)
            p_result = graph.run(c_string)
            uid_list = []
            for item in p_result:
                uid_list.append(item[0])
            result = get_detail_person(uid_list)#获取用户详细信息
            flag = 1
        elif card_key == event_primary:#group-event
            start_index_name = group_index_name
            end_index_name = event_index_name
            c_string = 'START n=node:%s("%s:*"),m=node:%s("%s:*") MATCH (n)-[]-()-[]-(m) return m.%s LIMIT 100' % (start_index_name,node_key,end_index_name,card_key,card_key)
            p_result = graph.run(c_string)
            uid_list = []
            for item in p_result:
                uid_list.append(item[0])
            result = get_detail_person(uid_list)#获取用户详细信息
            flag = 2
        else:#group-org
            start_index_name = group_index_name
            end_index_name = org_index_name
            c_string = 'START n=node:%s("%s:*"),m=node:%s("%s:*") MATCH (n)-[]-()-[]-(m) return m.%s LIMIT 100' % (start_index_name,node_key,end_index_name,card_key,card_key)
            p_result = graph.run(c_string)
            uid_list = []
            for item in p_result:
                uid_list.append(item[0])
            result = get_detail_org(uid_list)#获取用户详细信息
            flag = 0

    return result,flag
    



            
            














        
