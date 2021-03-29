from graphene import ObjectType, String, Field, Schema, List, Int
from fastapi import FastAPI
from starlette.graphql import GraphQLApp
import psycopg2
import json
import os

DBPASSWORD = os.environ.get('DBPASSWORD')
DBUSER = os.environ.get('DBUSER')


class Leshoz(ObjectType):
    leshoz_ru = String()
    leshoz_en = String()
    leshoz_id = Int()


class Oblast(ObjectType):
    oblast_ru = String()
    oblast_en = String()
    oblast_id = Int()
    leshoz_list = List(Leshoz)

    def resolve_leshoz_list(self, info):
        print(self.oblast_id)
        print('resole')
        leshoz_list_query = """SELECT leshoz_ru, leshoz_en, leshoz_id FROM forest.leshoz WHERE oblast_id={}""".format(
            self.oblast_id)
        conn = psycopg2.connect(dbname='forest_bd_work', user=DBUSER,
                                password=DBPASSWORD, host='192.168.31.177')
        cur = conn.cursor()
        cur.execute(leshoz_list_query)
        result = cur.fetchall()
        conn.commit()
        cur.close()
        resp = []
        print(result)
        for leshoz in result:
            print(leshoz)
            resp.append(
                Leshoz(leshoz_ru=leshoz[0], leshoz_en=leshoz[1], leshoz_id=leshoz[2]))
        return resp


class Query(ObjectType):
    oblast_list = List(Oblast)

    def resolve_oblast_list(self, info):
        oblast_list_query = """SELECT oblast_ru, oblast_en, oblast_id FROM topo.oblast"""
        conn = psycopg2.connect(dbname='forest_bd_work', user=DBUSER,
                                password=DBPASSWORD, host='192.168.31.177')
        cur = conn.cursor()
        cur.execute(oblast_list_query)
        result = cur.fetchall()
        conn.commit()
        cur.close()
        resp = []
        for oblast in result:
            print(oblast)
            resp.append(
                Oblast(oblast_ru=oblast[0], oblast_en=oblast[1], oblast_id=oblast[2]))
        return resp


app = FastAPI()

app.add_route("/", GraphQLApp(schema=Schema(query=Query)))
