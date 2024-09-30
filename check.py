import json
import jsonschema
from jsonschema import validate

# 数据格式检查
# 定义你的JSON模式
schema = {
    "type": "object",
    "properties": {
        "code": {"type": "int"},
        "message": {"type": "string"},
        "graphData": {"type": "object"},
        "agvData": {"type": "object"}
    },
    "required": ["graphData", "agvData"]
}

# JSON数据
data = '{"name": "John Doe", "age": 30, "is_student": false}'

# 将字符串转换为字典
data_dict = json.loads(data)

# 验证数据
try:
    validate(instance=data_dict, schema=schema)
    print("JSON数据有效")
except jsonschema.exceptions.ValidationError as err:
    print(f"JSON数据无效: {err}")
except jsonschema.exceptions.SchemaError as err:
    print(f"模式无效: {err}")


def check_init_data():
    pass


def check_graph_data():
    # 检查地图中每条边的长度是否大于安全间隔
    pass


def check_agv_data():
    pass
