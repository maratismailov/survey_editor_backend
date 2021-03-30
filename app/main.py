from graphene import ObjectType, String, Field, Schema, List, Int
from fastapi import FastAPI
from starlette.graphql import GraphQLApp
import psycopg2
import json
import os

DBPASSWORD = os.environ.get('DBPASSWORD')
DBUSER = os.environ.get('DBUSER')


class Block(ObjectType):
    block_num = Int()
    block_id = Int()


class Forestry(ObjectType):
    forestry_ru = String()
    forestry_en = String()
    forestry_id = Int()
    block_list = List(Block)

    def resolve_block_list(self, info):
        block_list_query = """SELECT block_num, gid FROM forest.block WHERE forestry_id={}""".format(
            self.forestry_id)
        conn = psycopg2.connect(dbname='forest_bd_work', user=DBUSER,
                                password=DBPASSWORD, host='192.168.31.177')
        cur = conn.cursor()
        cur.execute(block_list_query)
        result = cur.fetchall()
        conn.commit()
        cur.close()
        resp = []
        for block in result:
            resp.append(
                Block(block_num=block[0], block_id=block[1]))
        return resp


class Leshoz(ObjectType):
    leshoz_ru = String()
    leshoz_en = String()
    leshoz_id = Int()
    forestry_list = List(Forestry)

    def resolve_forestry_list(self, info):
        forestry_list_query = """SELECT forestry_ru, forestry_en, gid FROM forest.forestry WHERE leshoz_id={}""".format(
            self.leshoz_id)
        conn = psycopg2.connect(dbname='forest_bd_work', user=DBUSER,
                                password=DBPASSWORD, host='192.168.31.177')
        cur = conn.cursor()
        cur.execute(forestry_list_query)
        result = cur.fetchall()
        conn.commit()
        cur.close()
        resp = []
        for forestry in result:
            resp.append(
                Forestry(forestry_ru=forestry[0], forestry_en=forestry[1], forestry_id=forestry[2]))
        return resp


class Oblast(ObjectType):
    oblast_ru = String()
    oblast_en = String()
    oblast_id = Int()
    leshoz_list = List(Leshoz)

    def resolve_leshoz_list(self, info):
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
        for leshoz in result:
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
            resp.append(
                Oblast(oblast_ru=oblast[0], oblast_en=oblast[1], oblast_id=oblast[2]))
        return resp


app = FastAPI()

app.add_route("/", GraphQLApp(schema=Schema(query=Query)))
