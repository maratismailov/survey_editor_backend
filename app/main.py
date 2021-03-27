import graphene
from fastapi import FastAPI
from starlette.graphql import GraphQLApp


class Query(graphene.ObjectType):
    hello = graphene.String(name=graphene.String(default_value="stranger"))

    def resolve_hello(self, info, name):
        return "Hello " + name

class Second(graphene.ObjectType):
    second_hello = graphene.String(name=graphene.String(default_value="second stranger"))

    def resolve_second_hello(self, info, name):
        return "Second Hello " + name


app = FastAPI()

app.add_route("/", GraphQLApp(schema=graphene.Schema(query=Query)))

app.add_route("/3", GraphQLApp(schema=graphene.Schema(query=Second)))


@app.get("/2")
async def root():
    """
    example docstring
    """
    return {"message": "Hello World"}
