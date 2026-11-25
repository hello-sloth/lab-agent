
from pymilvus import MilvusClient, utility
client = MilvusClient(uri='http://tencent.hellosloth.top:19530',token="root:Milvus",db_name="rga_tutorial")
print(client.list_collections())

import requests
res = requests.post(

)
