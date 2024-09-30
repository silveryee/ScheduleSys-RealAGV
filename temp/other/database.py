import mysql.connector
# 数据库读取AGV以及静态地图数据


def create_adjacency_list(host, user, password, database):
    adjacency_list = {}

    # 连接到数据库
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()

        # 查询节点表
        cursor.execute("SELECT node_id FROM nodes")
        nodes = cursor.fetchall()

        for node in nodes:
            node_id = node[0]
            adjacency_list[node_id] = []

            # 查询与该节点相连的边
            cursor.execute("SELECT target_node_id FROM edges WHERE source_node_id=%s", (node_id,))
            edges = cursor.fetchall()

            for edge in edges:
                target_node_id = edge[0]
                adjacency_list[node_id].append(target_node_id)

    except mysql.connector.Error as e:
        print("数据库操作错误:", e)

    finally:
        # 关闭数据库连接
        conn.close() if 'conn' in locals() else None

    return adjacency_list


# MySQL 数据库连接配置
host = 'your_mysql_host'
user = 'your_mysql_user'
password = 'your_mysql_password'
database = 'your_mysql_database'

# 创建邻接表
adj_list = create_adjacency_list(host, user, password, database)

# 打印邻接表
for node_id, neighbors in adj_list.items():
    print(f"节点 {node_id}: 邻居 {neighbors}")