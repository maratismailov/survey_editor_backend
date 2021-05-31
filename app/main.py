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

from check_args import check_args

DBPASSWORD = os.environ.get('DBPASSWORD')
DBUSER = os.environ.get('DBUSER')
DBHOST = '192.168.31.177'
DBNAME = 'forest_bd_work'

DATABASE_URL = 'postgresql://' + DBUSER + ':' + DBPASSWORD +  '@192.168.31.177/forest_bd_work'

db = create_engine(DATABASE_URL)


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
    print(survey_id)
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
    query_text = db.execute("SELECT survey_body -> 'query_text' as initial_fields FROM mobile.templates WHERE survey_id ='{}'".format(id))
    for query in query_text:
        query_text = jsonable_encoder(query)['initial_fields']
    print(query_text)
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
    query_text = db.execute("SELECT survey_body -> 'query_text' as initial_fields, survey_body -> 'geom_field' as geom_field FROM mobile.templates WHERE survey_id ='{}'".format(id))
    for query in query_text:
        query_text = jsonable_encoder(query)['initial_fields']
        geom_field = jsonable_encoder(query)['geom_field']
    query_text = query_text.format(*ids)
    query_text = query_text.replace("*", "ST_XMin(ST_Extent({0})), ST_XMax(ST_Extent({0})), ST_YMin(ST_Extent({0})), ST_YMax(ST_Extent({0}))".format(geom_field))
    extent = db.execute(query_text)
    response = None
    result = ''
    for item in extent:
        response = jsonable_encoder(item)
        result = response
    padding = 0.003
    top = result['st_ymax'] + padding
    bottom = result['st_ymin'] - padding
    left = result['st_xmin'] - padding
    right = result['st_xmax'] + padding
    url = 'https://dev.forest.caiag.kg/mbtiles-generator/mbtiles?left=' + str(left) + '&bottom=' + str(bottom) + '&right=' + str(right) + '&top=' + str(top)
    print(url)
    urllib.request.urlretrieve(url, 'map.mbtiles')

    # https://dev.forest.caiag.kg/mbtiles-generator/mbtiles?left=72.7560069866762&bottom=41.3816081636863&right=72.7878707934176&top=41.417875180932

    # return json.dumps(result)
    return FileResponse('map.mbtiles', media_type="application/x-sqlite3")

@app.get("/generate_survey")
def generate_survey(id: str):
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
    # return 's'
    # response = None
    # result3 = []
    # for template in stand_list:
    #     response = jsonable_encoder(template)
    #     result.append(response)
    # return 's'
    return json.dumps(result)

@app.get("/get_initial_fields")
def get_initial_fields(id: str):
    results = db.execute("SELECT survey_body -> 'initial_fields' as initial_fields FROM mobile.templates WHERE survey_id ='{}'".format(id))
    response = None
    for template in results:
        response = jsonable_encoder(template)
    return json.dumps(response)