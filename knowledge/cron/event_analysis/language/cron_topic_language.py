# -*- coding: utf-8 -*-
import sys
import json,re
import datetime
#from topics import _all_topics

sys.path.append('../../../')
from time_utils import * #datetime2ts, ts2HourlyTime
from global_utils import event_analysis_name,event_type,event_text,event_text_type
from global_utils import es_event,es_user_portrait,portrait_index_name,portrait_index_type
from global_utils import bci_day_pre,bci_day_type
from parameter import RUN_TYPE,RUN_TEST_TIME
from global_utils import org_node,people_node,event_node,people_primary,org_primary,event_primary,node_index_name,event_index_name,org_index_name

sys.path.append('../../')
sys.path.append('../')
from get_relationship.get_pos import get_news_main #抽取事件的人物、机构、地点和时间
from event_classify.python.event_classify import cut_weibo #事件类型
from get_relationship.text_process import get_keyword,get_topic_word  #topic,keyword
def compute_real_info(topic,begin_ts,end_ts,relation):
	info_dict = {}
	
	query_body = {   
		'query':{
		'bool':{
		'must':[
		{'term':{'en_name':topic}},
		{'wildcard':{'text':'【*】*'}},
		{'range':{
		'timestamp':{'gte': begin_ts, 'lt':end_ts} 
		}
		}]
		}
		},
		'size':1,
		'sort':{'retweeted':{'order':'desc'}}
	}
	result = es_event.search(index=topic,doc_type=event_text_type,body=query_body)['hits']['hits']
	#抽取事件的人物、机构、地点和时间
	basics = get_news_main(result[0]['_source']['text'])

	info_dict['real_auth'] = basics['organization']
	info_dict['real_geo'] = basics['place']
	info_dict['real_time'] = basics['time']
	info_dict['real_person'] = basics['people']
	#存关系
	if('join' in relation.split('&')):
		rel_list = []
		if info_dict['real_auth'] !='None':
			resu = create_person(org_node,org_primary,info_dict['real_auth'],org_index_name)
			if resu != 'Node Wrong':
				rel_list.append([[2,en_name],'join',[0,info_dict['real_auth']]])
		if info_dict['real_person'] !='None':
			create_person(people_node,people_primary,info_dict['real_person'],node_index_name)
			if resu != 'Node Wrong':
				rel_list.append([[2,en_name],'join',[1,info_dict['real_person']]])
		try:
			nodes_rels(rel_list)
		except:
			pass

	query_body = {   
		'query':{
		'bool':{
		'must':[
		{'term':{'en_name':topic}},
		{'range':{
		'timestamp':{'gte': begin_ts, 'lt':end_ts} 
		}
		}]
		}
		},
		'size':10000
	}
	result = es_event.search(index=topic,doc_type=event_text_type,fields=['text'],body=query_body)['hits']['hits']
	text_list = []
	for i in result:
		text_list.append(i['fields']['text'][0])
	#print text_list
	#事件类型
	info_dict['category'] = cut_weibo(text_list)
	info_dict['topics'] = json.dumps(get_topic_word(text_list,10))
	
	keywords = get_keyword(''.join(text_list),2)
	info_dict['keywords'] = '&'.join([i[0] for i in keywords])
	info_dict['keywords_list'] = json.dumps(keywords)

	hashtag = get_hashtag(''.join(text_list))
	info_dict['hashtag_dict'] = json.dumps(hashtag)
	info_dict['hashtag'] = '&'.join(list(hashtag.keys()))
	

	try:
		es_event.update(index=event_analysis_name,doc_type=event_type,id=topic,body={'doc':info_dict})
	except Exception,e:
		es_event.index(index=event_analysis_name,doc_type=event_type,id=topic,body=info_dict)
	get_users(topic,begin_ts,end_ts,relation)


def get_hashtag(text):
	if isinstance(text, str):
		text = text.decode('utf-8', 'ignore')
	RE = re.compile(u'#([a-zA-Z-_⺀-⺙⺛-⻳⼀-⿕々〇〡-〩〸-〺〻㐀-䶵一-鿃豈-鶴侮-頻並-龎]+)#', re.UNICODE)
	hashtag_list = RE.findall(text)
	hashtag_dict = dict()
	if hashtag_list:
		for hashtag in hashtag_list:
			try:
				hashtag_dict[hashtag] += 1
			except:
				hashtag_dict[hashtag] = 1
	return hashtag_dict

def get_users(topic,begin_ts,end_ts,relation):
	uid_list = set()
	query_body = {   
		'query':{
		'bool':{
		'must':[
		{'term':{'en_name':topic}},
		# {'wildcard':{'text':'【*】*'}},
		{'range':{
		'timestamp':{'gte': begin_ts, 'lt':end_ts} 
		}
		}]
		}
		},
		'size':999999999
	}
	result = es_event.search(index=topic,doc_type=event_text_type, fields=['text'],body=query_body)['hits']['hits']
	for i in result:
		uid_list.add(i['fields']['uid'][0])
	print len(uid_list)
	if RUN_TYPE == 0:
		post = datetime2ts(RUN_TEST_TIME) #datetimestr2ts(RUN_TEST_TIME) 
		post = ts2datetimestr(post)
	else:
		post = ts2datetimestr(time.time())
		
	print  bci_day_pre+post,bci_day_type,es_user_portrait
	user_result = es_user_portrait.mget(index=bci_day_pre+post ,doc_type=bci_day_type,body={'ids':list(uid_list)})['docs']
	
	user_influence_dict = {}
	for i in user_result:
		#print i
		if i['found']:
			i = i['_source']
			user_influence_dict[i['user']] = i['user_index']
			#print i,type(i)
			
			#print i['activeness'],i['influence'],i['fansnum']

	user = sorted(user_influence_dict.iteritems(),key=lambda x:x[1],reverse=True)[:100]
	#print user
	user_dict = {}
	p_list = []
	a_list = []
	for i in user:
		try:
			result = es_user_profile.get(index=profile_index_name,doc_type=profile_index_type,id=i[0])
			u_type = result['_source']['verified_type']
			if u_type in auth_list:
				u_type = auth_type
				a_list.append(i[0])
			else:
				u_type = user_type
				p_list.append(i[0])
			user_dict[i[0]] = {'user_type':u_type,'influ':i[1]}

		except:
			user_dict[i[0]] = {'user_type':user_type,'influ':i[1]}
			p_list.append(i[0])

	if('discuss' in relation.split('&')):
		rel_list = []
		for i in p_list:
			resu = create_person(people_node,people_primary,i,node_index_name)
			if resu != 'Node Wrong':
				rel_list.append([[2,en_name],'discuss',[1,i]])
		for i in a_list:
			resu = create_person(org_node,org_primary,i,org_index_name)
			if resu != 'Node Wrong':
				rel_list.append([[2,en_name],'discuss',[0,i]])
		try:
			nodes_rels(rel_list)
		except:
			pass


	try:
		es_event.update(index=event_analysis_name,doc_type=event_type,id=topic,body={'doc':{'user_results':json.dumps(user_dict)}})
	except Exception,e:
		es_event.index(index=event_analysis_name,doc_type=event_type,id=topic,body={'user_results':json.dumps(user_dict)})


if __name__ == '__main__':
	topic = 'zui_gao_fa_di_zhi_yan_se_ge_ming'
	start_date = 1484323200#'2017-01-14'
	end_date = 1484582400#'2017-01-17'

	#get_users(topic,start_date,end_date)
	compute_real_info(topic,start_date,end_date)