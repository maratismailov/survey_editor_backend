from graphene import ObjectType, String, Field, Schema, List, Int
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.graphql import GraphQLApp
import json
import os
import urllib.request
from sqlalchemy import create_engine
from fastapi.encoders import jsonable_encoder
import base64
import requests
import re

from check_args import check_args

DBPASSWORD = os.environ.get('DBPASSWORD')
DBUSER = os.environ.get('DBUSER')
DBHOST = os.environ.get('DBHOST')
DBNAME = os.environ.get('DBNAME')

DATABASE_URL = 'postgresql://' + DBUSER + ':' + DBPASSWORD +  '@' + DBHOST + '/' + DBNAME

db = create_engine(DATABASE_URL)
woodspecies = []


class Stand(ObjectType):
    stand_code = Int()
    stand_id = Int()

class Block(ObjectType):
    block_num = Int()
    block_id = Int()
    stand_list = List(Stand)

    def resolve_stand_list(self, info):
        results = db.execute("""SELECT stand_code, gid FROM forest.stand WHERE block_id={}""".format(
            self.block_id))
        resp = []
        for stand in results:
            resp.append(
                Stand(stand_code=stand[0], stand_id=stand[1]))
        return resp


class Forestry(ObjectType):
    forestry_ru = String()
    forestry_en = String()
    forestry_id = Int()
    block_list = List(Block)

    def resolve_block_list(self, info):
        results = db.execute("""SELECT block_num, gid FROM forest.block WHERE forestry_id={}""".format(
            self.forestry_id))
        resp = []
        for block in results:
            resp.append(
                Block(block_num=block[0], block_id=block[1]))
        return resp


class Leshoz(ObjectType):
    leshoz_ru = String()
    leshoz_en = String()
    leshoz_id = Int()
    forestry_list = List(Forestry)

    def resolve_forestry_list(self, info):
        results = db.execute("""SELECT forestry_ru, forestry_en, gid FROM forest.forestry WHERE leshoz_id={}""".format(
            self.leshoz_id))
        resp = []
        for forestry in results:
            resp.append(
                Forestry(forestry_ru=forestry[0], forestry_en=forestry[1], forestry_id=forestry[2]))
        return resp


class Oblast(ObjectType):
    oblast_ru = String()
    oblast_en = String()
    oblast_id = Int()
    leshoz_list = List(Leshoz)

    def resolve_leshoz_list(self, info):
        results = db.execute("""SELECT leshoz_ru, leshoz_en, leshoz_id FROM forest.leshoz WHERE oblast_id={}""".format(
            self.oblast_id))
        resp = []
        for leshoz in results:
            resp.append(
                Leshoz(leshoz_ru=leshoz[0], leshoz_en=leshoz[1], leshoz_id=leshoz[2]))
        return resp


class Select(ObjectType):
    id = Int()
    name = String()

class Query(ObjectType):
    oblast_list = List(Oblast)
    select_list = List(Select, table_name=String(), name_column=String(), id_column=String(), where_clause=String())

    def resolve_select_list(self, info, table_name, name_column, id_column, where_clause=''):
        resp = []
        args = [table_name, name_column, id_column]
        if check_args(args) == 'not valid':
            return
        query = "SELECT " + id_column + ", " + name_column + " FROM forest." + table_name + " " + where_clause
        # query = query.replace(',,', ',')
        # query = query.replace(', FROM', ' FROM')
        results = db.execute(query)
        for row in results:
            resp.append(Select(id=row[0], name=row[1]))
        return resp

    def resolve_oblast_list(self, info):
        results = db.execute("SELECT oblast_ru, oblast_en, oblast_id FROM topo.oblast")
        resp = []
        for oblast in results:
            resp.append(
                Oblast(oblast_ru=oblast[0], oblast_en=oblast[1], oblast_id=oblast[2]))
        return resp


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_route("/", GraphQLApp(schema=Schema(query=Query)))

@app.post("/save_survey_template")
async def save_survey_template(request: Request, id:  str = ""):
    data = await request.json()
    survey_id = data['survey_id']
    name = data['name']
    data = json.dumps(data)
    data = data.replace("'","''")
    ids = db.execute("SELECT survey_id FROM mobile.templates")
    for id_num in ids:
        if id == id_num[0]:
            query = db.execute("UPDATE mobile.templates SET (survey_body, survey_name) = ('{}', '{}') WHERE survey_id = '{}'".format(data, name, id))
            return 'success'
    query = db.execute("INSERT INTO mobile.templates (survey_id, survey_name, survey_body) VALUES ('{}', '{}', '{}')".format(survey_id, name, data))
    return 'success'


@app.get("/get_templates_list")
def get_templates_list():
    templates_list = db.execute("SELECT survey_id, survey_name FROM mobile.templates")
    a_list = []
    for template in templates_list:
        a_list.append(jsonable_encoder(template))
    response = json.dumps(a_list)
    return response

@app.get("/get_template_by_id")
def get_template_by_id(id: str):
    results = db.execute("SELECT survey_body as survey FROM mobile.templates WHERE survey_id ='{}'".format(id))
    response = None
    for template in results:
        response = jsonable_encoder(template)
    return json.dumps(response)

@app.get("/generate_objects")
def generate_objects(id: str, values: str):
    values = json.loads(values)
    ids = []
    for value in values:
        ids.append(value['value'])
    query_text = db.execute("SELECT survey_body -> 'objects_query_text' as query_text FROM mobile.templates WHERE survey_id ='{}'".format(id))
    for query in query_text:
        query_text = jsonable_encoder(query)['query_text']
    query_text = query_text.format(*ids)
    stand_list = db.execute(query_text)
    # results = db.execute("SELECT survey_body as survey FROM mobile.templates WHERE survey_id ='{}'".format(id))
    response = None
    result = []
    for template in stand_list:
        response = jsonable_encoder(template)
        result.append(response)
    return json.dumps(result)

@app.get("/generate_mbtiles")
def generate_mbtiles(id: str, values: str):
    values = json.loads(values)
    ids = []
    for value in values:
        ids.append(value['value'])
    # geom_field_query = db.execute("SELECT survey_body -> 'geom_field' as geom_field FROM mobile.templates WHERE survey_id ='{}'".format(id))
    # query_text = db.execute("SELECT survey_body -> 'bounds_query_text' as initial_fields, survey_body -> 'geom_field' as geom_field, survey_body -> 'object_code' as object_code FROM mobile.templates WHERE survey_id ='{}'".format(id))
    query_text = db.execute("SELECT survey_body -> 'bounds_query_text' as query_text FROM mobile.templates WHERE survey_id ='{}'".format(id))
    for query in query_text:
        query_text = jsonable_encoder(query)['query_text']
        # geom_field = jsonable_encoder(query)['geom_field']
        # obj_field = jsonable_encoder(query)['object_code']
    query_text = query_text.format(*ids)
    # query_text = query_text.replace(geom_field, "ST_XMin(ST_Extent({0})), ST_XMax(ST_Extent({0})), ST_YMin(ST_Extent({0})), ST_YMax(ST_Extent({0}))".format(geom_field))
    # query_text = query_text.replace('ST_AsGeoJSON', '')
    # query_text = query_text.replace(obj_field, "")
    # query_text = query_text.replace(',  FROM', 'FROM')
    extent = db.execute(query_text)
    response = None
    print('1st', extent)
    for item in extent:
        response = (jsonable_encoder(item))
        result = response
    padding = 0.003
    # result = result.strip(')(').split(',')
    print('resutl', result)
    top = float(result['st_ymax']) + padding
    bottom = float(result['st_ymin']) - padding
    left = float(result['st_xmin']) - padding
    right = float(result['st_xmax']) + padding
    url = 'https://dev.forest.caiag.kg/mbtiles-generator/mbtiles?left=' + str(left) + '&bottom=' + str(bottom) + '&right=' + str(right) + '&top=' + str(top)
    print('url', url)
    urllib.request.urlretrieve(url, 'map.mbtiles')
    # https://dev.forest.caiag.kg/mbtiles-generator/mbtiles?left=72.7560069866762&bottom=41.3816081636863&right=72.7878707934176&top=41.417875180932
    # return json.dumps(result)
    return FileResponse('map.mbtiles', media_type="application/x-sqlite3")

@app.get("/generate_survey")
def generate_survey(id: str, values: str):
    query = db.execute("SELECT survey_body FROM mobile.templates WHERE survey_id ='{}'".format(id))
    for elem in query:
        result = jsonable_encoder(elem)
    for elem in result['survey_body']['survey_body']:
        if elem['type'] == 'select':
            name = elem['select']['name_column']
            code = elem['select']['id_column']
            table = elem['select']['table_name']
            where_clause = elem['select']['where_clause']
            query_text = 'SELECT ' + name + ' ' + 'AS name, ' + code + ' ' + 'AS code ' + 'FROM ' + table + ' ' + where_clause
            results = db.execute(query_text)
            response = None
            result2 = []
            for value in results:
                response = jsonable_encoder(value)
                result2.append(response)
            elem['select_values'] = result2
        elif elem['type'] == 'table':
            for table_elem in elem['fields'][0]:
                if table_elem['type'] == 'select':
                    name = table_elem['select']['name_column']
                    code = table_elem['select']['id_column']
                    table = table_elem['select']['table_name']
                    where_clause = table_elem['select']['where_clause']
                    query_text = 'SELECT ' + name + ' ' + 'AS name, ' + code + ' ' + 'AS code ' + 'FROM ' + table + ' ' + where_clause
                    results = db.execute(query_text)
                    response = None
                    result2 = []
                    for value in results:
                        response = jsonable_encoder(value)
                        result2.append(response)
                    table_elem['select_values'] = result2

    values = json.loads(values)
    ids = []
    for value in values:
        ids.append(value['value'])
    survey_ids = []
    for item in result['survey_body']['survey_body']:
        survey_ids.append(item['id'])
        print(item['id'])
    get_complete_surveys(id, ids, survey_ids)

    return
    bounds_query_text = db.execute("SELECT survey_body -> 'bounds_query_text' as query_text FROM mobile.templates WHERE survey_id ='{}'".format(id))
    for query in bounds_query_text:
        bounds_query_text = jsonable_encoder(query)['query_text']
    #     geom_field = jsonable_encoder(query)['geom_field']
    #     obj_field = jsonable_encoder(query)['object_code']
    bounds_query_text = bounds_query_text.format(*ids)
    # orig_query = geom_query_text
    # geom_query_text = geom_query_text.replace(geom_field, "ST_Centroid(ST_Extent(the_geom))")
    # geom_query_text = geom_query_text.replace(obj_field, "")
    # geom_query_text = geom_query_text.replace(',  FROM', 'FROM')
    # center = db.execute(geom_query_text)
    # response = None
    # geom_result = ''
    # for item in center:
    #     response = jsonable_encoder(item)
    #     geom_result = response
    # extent_query = orig_query
    # extent_query = extent_query.replace(obj_field, "")
    # extent_query = extent_query.replace(',  FROM', 'FROM')
    # extent_query = extent_query.replace('ST_AsGeoJSON', "")
    # extent_query = extent_query.replace(geom_field, "ST_XMin(ST_Extent({0})), ST_XMax(ST_Extent({0})), ST_YMin(ST_Extent({0})), ST_YMax(ST_Extent({0}))".format(geom_field))
    # extent = db.execute(bounds_query_text)
    # response = None
    # extent_result = ''

    # extent_result = extent_result['row']
    # for item in extent_result:
    #     response = (jsonable_encoder(item)['row'])
    #     result = response
    # padding = 0.003
    extent = db.execute(bounds_query_text)
    response = None
    for item in extent:
        response = jsonable_encoder(item)
        extent_result = response
    print('2nd', extent)
    for item in extent:
        response = (jsonable_encoder(item))
        extent_result = response
    print('result', extent_result)
    # extent_result = result.strip(')(').split(',')
    # for item in extent_result:
    #     print('item', item)
        # item = float(item)
    # top = geom_result['st_ymax']
    # bottom = geom_result['st_ymin']
    # left = geom_result['st_xmin']
    # right = geom_result['st_xmax']
    # vert_center = (top + bottom)/2
    # horiz_center = (left + right)/2
    # print(vert_center, horiz_center)
    # return 's'
    # response = None
    # result3 = []
    # for template in stand_list:
    #     response = jsonable_encoder(template)
    #     result.append(response)
    # return 's'
    result['initial_fields'] = values
    result['bounds'] = extent_result
    print(result['bounds'])
    # result['center'] = json.loads(geom_result['st_asgeojson'])['coordinates']
    return json.dumps(result)

def get_complete_surveys(id, ids, survey_ids):
    print(id, ids)
    if (id == 'stand_estimation_leshoz'):
        get_stand_estimation_leshoz_complete_surveys(ids, survey_ids)

def get_stand_estimation_leshoz_complete_surveys(ids, survey_ids):
    survey_ids2 = []
    # for id in survey_ids:
    #     if id !=

    not_to_include = ['forestcomposition', 'standforestuse', 'ecoproblem_id', 'plannedcomposition', 'actionsfirstpriority', 'standplanuse1', 'soilprocessing1', 'speciescreation1', 'actionssecondpriority', 'standplanuse2',  'soilprocessing2', 'speciescreation2']
    st = 'siteadmin'
    for id in survey_ids:
        if not any([x in id for x in not_to_include]):survey_ids2.append(id)
    # protectcategory_id,foresttype_id,stand_num,oldstandnums,landcategory_id,exploitationcat_id,exposition_id,forestorigin_id,layerage_id,evolutionstage_id,forestcomposition,ageclass_id,crowndensity_id,marketability_id,sanitarystate_id,stability_id,renewalstate_id,underbrush_id,cattlepasture_id,forestuseorgform_id,standforestuse,burl_id,addinfo,firehazardclass_id,ecoproblem_id,grasscover_id,steepness_id,clutter,economy_id,purpose_id,plannedcomposition,actionsfirstpriority,planuseorgform1_id,standplanuse1,soilprocessing1,speciescreation1,additionact1,actionssecondpriority,planuseorgform2_id,standplanuse2,soilprocessing2,speciescreation2,additionact2


    print('s ids', ','.join(survey_ids))
    print('s ids2', ','.join(survey_ids2))
    query = db.execute("SELECT standestimation_id, {} FROM forest.standestimation WHERE leshoz_id ='{}' and forestry_num ='{}' and block_num ='{}' order by stand_num".format(','.join(survey_ids2), ids[0], ids[1], ids[2]))
    result = []
    species_query = db.execute("SELECT woodspecies_id, woodshortname FROM forest.woodspecies")
    species_result = []
    for elem in species_query:
        woodspecies.append(jsonable_encoder(elem))
    for elem in query:
        result.append(jsonable_encoder(elem))
    for item in result:
        get_standestimation_table_data(item['standestimation_id'])
    print(woodspecies)
    # print(result)

def get_standestimation_table_data(standestimation_id):
    print(standestimation_id)
    forest_composition = get_forest_composition(standestimation_id, 1)

def get_forest_composition(standestimation_id, plan_fact):
    forest_compostion_query = db.execute("SELECT woodspecies_id, species_percent FROM forest.forestcomposition WHERE standestimation_id = {} AND plan_fact = {}".format(standestimation_id, plan_fact))
    forest_compostion_result = []
    for elem in forest_compostion_query:
        forest_compostion_result.append(jsonable_encoder(elem))
    print(standestimation_id, plan_fact, forest_compostion_result)


@app.get("/get_initial_fields")
def get_initial_fields(id: str):
    results = db.execute("SELECT survey_body -> 'initial_fields' as initial_fields FROM mobile.templates WHERE survey_id ='{}'".format(id))
    response = None
    for template in results:
        response = jsonable_encoder(template)
    return json.dumps(response)


@app.get("/send_standestimation_data")
def send_standestimation_data(data: str):
    # print(data)
    data = json.loads(data)
    for item in data:
        if item['id'] == 'Номер лесхоза':
            item['id'] =  'leshoz_id'
            leshoz_id = item['val']
        elif item['id'] == 'Номер лесничества':
            forestry_num = item['val']
            item['id'] = 'forestry_num'
        elif item['id'] == 'Номер квартала':
            item['id'] = 'block_num'
            block_num = item['val']
        elif item['id'] == 'exposition_id':
            exposition_val = item['val']
        elif item['id'] == 'stand_num':
            stand_num = item['val']
        elif item['id'] == 'landcategory_id':
            landcategory = item['val']
        elif item['id'] == 'foresttype_id':
            foresttype = item['val']
        elif item['id'] == 'forestcomposition':
            forestcomposition = item['val']
        elif item['id'] == 'plannedcomposition':
            plannedcomposition = item['val']
        elif item['id'] == 'protectcategory_id':
            protectcategory = item['val']
        elif item['id'] == 'new_geometries':
            new_geometries = item['val']
            item['val'] = None
        elif item['id'] == 'geometries_to_delete':
            geometries_to_delete = item['val']
            item['val'] = None

    for item in data:
        if 'soilprocessing' in item['id']:
            try:
                item['val'] = get_soilprocessing(item['val'])
            except:
                print('nodata')
        elif 'speciescreation' in item['id']:
            try:
                item['val'] = get_speciescreation(item['val'])
            except:
                print('nodata')
    # print(leshoz_id, forestry_num, block_num)
    try:
        forestry_id = get_forestry_id(leshoz_id, forestry_num)
    except:
        print('nodata')
    try:
        block_id = get_block_id(forestry_id, block_num)
    except:
        print('nodata')
    try:
        oblast_id = get_oblast_id(leshoz_id)
    except:
        print('nodata')
    try:
        exposition_id = get_expostition_id(exposition_val)
    except:
        exposition_id = None
        print('nodata')
    try:
        print('standcode', leshoz_id, forestry_num, block_num, stand_num)
        stand_code = get_standcode(leshoz_id, forestry_num, block_num, stand_num)
    except:
         print('nodata')
    try:
        landcategory_id = get_landcategory_id(landcategory)
    except:
         print('nodata')
    try:
        foresttype_id = get_foresttype_id(foresttype)
    except:
         print('nodata')
    try:
        protectcategory_id = get_protectcategory_id(protectcategory)
    except:
         print('nodata')
    # soilprocessing_id = get_soilprocessing()
    # print(stand_code)
    if stand_code is not None:
        data.append({'id': 'stand_code', 'val': str(stand_code)})
        standestimation_id = get_standestimation_id(stand_code)
        data.append({'id': 'standestimation_id', 'val': str(standestimation_id)})
        for item in data:
            if item['id'] == 'stand_num':
                item['val'] = ''
    # print(forestry_id, block_id)
    data.append({'id': 'forestry_id', 'val': str(forestry_id)})
    data.append({'id': 'block_id', 'val': str(block_id)})
    data.append({'id': 'oblast_id', 'val': str(oblast_id)})
    data.append({'id': 'unprocessed_flag', 'val': 0})
    data.append({'id': 'standestimation_cycle', 'val': '2'})
    data.append({'id': 'acttype', 'val': []})
    ext_forest_composition = get_forestcomposition(forestcomposition, 'forestcomposition')
    ext_planned_composition = get_forestcomposition(plannedcomposition, 'plannedcomposition')
    for item in data:
        print(item)
        if item['id'] == 'exposition_id':
            item['val'] = str(exposition_id)
        elif item['id'] == 'block_num':
            item['val'] = ''
        elif item['id'] == 'landcategory_id':
            item['val'] = landcategory_id
        elif item['id'] == 'protectcategory_id':
            item['val'] = protectcategory_id
        elif item['id'] == 'foresttype_id':
            item['val'] = foresttype_id
        elif item['id'] == 'forestcomposition':
            item['val'] = ''
        elif item['id'] == 'plannedcomposition':
            item['val'] = ''
    data.extend(ext_forest_composition)
    data.extend(ext_planned_composition)

    # for item in data:
    #     print('acttype', item)
    # return 'composition'

    # for item in data:
    #     print(item)
    # f = open('payload.json',)
    # data = json.load(f)
    new_geometries = json.loads(new_geometries)
    # print('new', new_geometries)
    for item in new_geometries:
        print(leshoz_id, forestry_num, block_num)
        print('new', item['properties']['id'])
        result = db.execute("select stand_num from forest.stand where leshoz_num = '{}' and forestry_num = '{}' and block_num = '{}' and stand_num = '{}'".format(leshoz_id, forestry_num, block_num, item['properties']['id']))
        response = None
        for data in result:
            response = jsonable_encoder(data)
        if response is not None:
            print('res', response)
        else:
            print('none')
            # query = db.execute("INSERT INTO forest.stand (survey_id, survey_name, survey_body) VALUES ('{}', '{}', '{}')".format(survey_id, name, data))

    print('delete', geometries_to_delete)
    print('block_id', block_id)
    return
    data_bytes = json.dumps(data).encode("utf-8")
    # Opening JSON file
    # f = open('payload.json',)
    # data = json.load(f)
    # print(data_bytes)
    # data64 = base64.b64encode(data_bytes)
    # data64 = data64.decode('ascii')
    # post_data = {}
    # post_data['base64'] = data64
    # post_data = json.dumps(post_data)
    # print(post_data)
    url = 'https://dev.forest.caiag.kg/ru/rent/standest/savestandestform'
    # post = urllib.request.urlopen(url, data=bytes(post_data), encoding="ascii")

    post_data = urllib.parse.urlencode({'base64': base64.b64encode(data_bytes)})
    post_data = post_data.encode('utf-8')
    # print(post_data)
    user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
    # headers = { 'User-Agent' : user_agent,
    #         'Content-type': "application/x-www-form-urlencoded",
    #         'Accept': "text/plain"}
    headers = {'User-Agent': 'Mozilla/5.0'}
    request = urllib.request.Request(url, data=post_data, headers=headers)
    # cookies = """show_red_items=1; _ga=GA1.2.631020320.1617350960; _ym_uid=161735096089548495; _ym_d=1617350960; _identity-frontend=a70afbde4814fde870f8fc974326e10c5ed40718117659e178080a4a3e2c4e7fa%3A2%3A%7Bi%3A0%3Bs%3A18%3A%22_identity-frontend%22%3Bi%3A1%3Bs%3A47%3A%22%5B76%2C%22yfPlk9L4YADp1bagnvrodpC1NIEucZ-w%22%2C2592000%5D%22%3B%7D; _csrf=dc45c1e918cb2b184c4082fe66deda44fc940e142446f74eae526b4c36c8fe13a%3A2%3A%7Bi%3A0%3Bs%3A5%3A%22_csrf%22%3Bi%3A1%3Bs%3A32%3A%22v00ig2tViiRAyYum94QXHo1nOS3Tgw-5%22%3B%7D; advanced-frontend=vepbsmkhen05f9rvcq71rkv6a0"""
    # cookies={'show_red_items':1, '_ga':'GA1.2.631020320.1617350960', '_ym_uid':161735096089548495, '_ym_d':1617350960, '_identity-frontend':'a70afbde4814fde870f8fc974326e10c5ed40718117659e178080a4a3e2c4e7fa%3A2%3A%7Bi%3A0%3Bs%3A18%3A%22_identity-frontend%22%3Bi%3A1%3Bs%3A47%3A%22%5B76%2C%22yfPlk9L4YADp1bagnvrodpC1NIEucZ-w%22%2C2592000%5D%22%3B%7D', '_csrf':'dc45c1e918cb2b184c4082fe66deda44fc940e142446f74eae526b4c36c8fe13a%3A2%3A%7Bi%3A0%3Bs%3A5%3A%22_csrf%22%3Bi%3A1%3Bs%3A32%3A%22v00ig2tViiRAyYum94QXHo1nOS3Tgw-5%22%3B%7D', 'advanced-frontend':'vepbsmkhen05f9rvcq71rkv6a0'}
    login_url = 'https://dev.forest.caiag.kg/ru/site/login'
    # payload={'username': "m_ismailov",'password': "5caiag275"}
    # session = requests.Session()
    # resp1 = session.post(login_url, data=payload, headers=headers)
    # print('cookies', resp1.text)
    # resp2 = requests.post(url, cookies=resp1.cookies, data=post_data, headers=headers)
    # resp2 = requests.post(url, data=post_data, headers=headers)
    # response = requests.post(url, headers=headers).text
    # print(request)
    response = urllib.request.urlopen(request).read()
    print('response', response)
    # results = db.execute("SELECT survey_body -> 'initial_fields' as initial_fields FROM mobile.templates WHERE survey_id ='{}'".format(id))
    # response = None
    # for template in results:
    #     response = jsonable_encoder(template)
    return 's'
    return json.dumps(response)


def get_forestry_id(leshoz_id, forestry_num):
    result = db.execute("select gid from forest.forestry f where leshoz_id = '{}' and forestry_num = '{}'".format(leshoz_id, forestry_num))
    response = None
    for data in result:
        response = jsonable_encoder(data)
    return response['gid']

def get_block_id(forestry_id, block_num):
    result = db.execute("select gid from forest.block b where forestry_id = '{}' and block_num = '{}'".format(forestry_id, block_num))
    response = None
    for data in result:
        response = jsonable_encoder(data)
    return response['gid']

def get_oblast_id(leshoz_id):
    result = db.execute("select oblast_id from forest.leshoz l where leshoz_id = '{}'".format(leshoz_id))
    response = None
    for data in result:
        response = jsonable_encoder(data)
    return response['oblast_id']

def get_expostition_id(exposition_val):
    exposition_val = exposition_val.upper()
    print('exp', exposition_val)
    result = db.execute("select exposition_id from forest.exposition e where abbreviation = '{}'".format(exposition_val))
    response = None
    for data in result:
        response = jsonable_encoder(data)
    return response['exposition_id']


def get_standcode(leshoz_id, forestry_num, block_num, stand_num):
    result = db.execute("select stand_code from forest.stand where leshoz_num = '{}' and forestry_num = '{}' and block_num = '{}' and stand_num = '{}'".format(leshoz_id, forestry_num, block_num, stand_num))
    response = None
    for data in result:
        response = jsonable_encoder(data)
    if response == None:
        return None
    print('resp', response)
    return response['stand_code']

def get_standestimation_id(stand_code):
    result = db.execute("select standestimation_id from forest.standestimation s where stand_code = '{}'".format(stand_code))
    response = None
    for data in result:
        response = jsonable_encoder(data)
    return response['standestimation_id']

def get_landcategory_id(landcategory):
    result = db.execute("select landtype_id from forest.landtype l where landtype_code = '{}'".format(landcategory))
    response = None
    for data in result:
        response = jsonable_encoder(data)
    return response['landtype_id']

def get_protectcategory_id(protectcategory):
    result = db.execute("select  protectcategory_id from forest.protectcategory p where protectcategory_code = '{}'".format(protectcategory))
    response = None
    for data in result:
        response = jsonable_encoder(data)
    return response['protectcategory_id']

def get_foresttype_id(foresttype):
    result = db.execute("select foresttype_id from forest.foresttype f where foresttype_code = '{}'".format(foresttype))
    response = None
    for data in result:
        response = jsonable_encoder(data)
    return response['foresttype_id']

def get_soilprocessing(f_code):
    result = db.execute("select actiontype_id from forest.actiontype where f_type = 'f31' and f_code = '{}' and oopt_flag = 0".format(f_code))
    response = None
    for data in result:
        response = jsonable_encoder(data)
    return response['actiontype_id']

def get_speciescreation(f_code):
    result = db.execute("select actiontype_id from forest.actiontype where f_type = 'f32' and f_code = '{}' and oopt_flag = 0".format(f_code))
    response = None
    for data in result:
        response = jsonable_encoder(data)
    return response['actiontype_id']


def get_forestcomposition(abbreviation, name):
    abbreviation = abbreviation.upper()
    result = db.execute("select woodspecies_id, woodshortname from forest.woodspecies w")
    response = None
    woodspecies_list = []
    for data in result:
        response = jsonable_encoder(data)
        woodspecies_list.append(response)
    pre_compose = []
    pre_compose = re.findall("\d*[а-яА-Я]*|\+*[а-яА-Я]*", abbreviation)
    compose_string = []
    for item in pre_compose:
        if item != '':
            compose_string.append(item)
    compose = []
    for index, item in enumerate(compose_string):
        woodspecies = ''
        species_percent = ''
        percent = re.findall("\d|\+|$", item)[0]
        shortname = re.findall("[а-яА-Я]+|$", item)[0]
        if percent == '+':
            percent = 0
        percent = int(percent) * 10
        woodspecies_id = 0
        for item in woodspecies_list:
            if item['woodshortname'] == shortname:
                woodspecies_id = item['woodspecies_id']
        i = (index + 1) * -1
        woodspecies = {'id': name + '.woodspecies.'+str(i), 'val': woodspecies_id}
        species_percent = {'id': name + '.species_percent.'+str(i), 'val': str(percent)}
        compose.append(woodspecies)
        compose.append(species_percent)
    return compose
# 4ад4б2гл+орг
# 5орг3б2гл+ад

# calcShortMainString(event) {
#         this.many_main_compose = false;
#         const pre_result = event.target.value.toUpperCase();
#         const result = pre_result.match(/(\d*[а-яА-Я]*)/g);
#         // const result = pre_result.match(/([1-9][а-яА-Я]*)/g);
#         const result2 = result.filter(el => {
#           return el != "";
#         });
#         const result3 = result2.map(elem => {
#           return elem.replace(/([а-яА-Я]+)/g, " $1 ");
#         });
#         const result5 = result3.map(elem => {
#           return elem.split(" ");
#         });
#         const ids = [];
#         result5.map(elem => {
#           ids.push(
#             this.journal.composition.find(elem2 => {
#               return elem2.woodshortname == elem[1];
#             })
#           );
#         });
#         const main_undef = elem => elem == undefined;
#         this.error_main_compose = ids.some(main_undef);
#         this.maincomposition = result5.map((elem, index) => {
#           return {
#             species_percent: elem[0] * 10,
#             woodshortname: elem[1],
#             woodspecies_id: ids[index].woodspecies_id
#           };
#         });
#         if (this.maincomposition.length > 1) {
#           this.many_main_compose = true;
#           // this.maincomposition.length = 1
#         }
#         // this.maincomposition = new_composition;

#     }
