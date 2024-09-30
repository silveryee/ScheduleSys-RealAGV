class MyDirectedGraph:
    def __init__(self, data=None):
        self.vertex = []
        self.edge = {}
        if data:
            for pair in data:
                from_node = pair[0]
                to_node = pair[1]
                edge_weight = pair[2]
                if from_node not in self.vertex:
                    self.vertex.append(from_node)
                if to_node not in self.vertex:
                    self.vertex.append(to_node)
                if from_node in self.edge:
                    self.edge[from_node].append([to_node, edge_weight])
                else:
                    self.edge[from_node] = [[to_node, edge_weight]]

    def _valid(self, v):
        return v in self.vertex

    def is_empty(self):
        return len(self.vertex) == 0

    def vertex_num(self):
        return len(self.vertex)

    def edge_num(self):
        res = 0
        for key, value in self.edge.items():
            res += len(value)
        return res

    def vertices(self):
        return self.vertex

    def edges(self):
        res = []
        for key in self.edge:
            edge_list = self.edge[key]
            for i in range(len(edge_list)):
                item = [key] + edge_list[i]
                res.append(item)
        return res

    def add_vertex(self, v):
        if v not in self.vertex:
            self.vertex.append(v)
        else:
            raise ValueError('Node has been in graph!')

    def add_edge(self, v1, v2, w):
        if self._valid(v1) and self._valid(v2):
            if v1 in self.edge:
                edge_list = self.edge[v1]
                for i in range(len(edge_list)):
                    if edge_list[i][0] == v2:
                        edge_list[i][2] = w
                        return
                edge_list.append([v2, w])
            else:
                self.edge[v1] = [[v2, w]]
        else:
            raise ValueError('Node not in graph!')

    def get_edge(self, v1, v2):
        if self._valid(v1) and self._valid(v2):
            if v1 in self.edge:
                edge_list = self.edge[v1]
                for i in range(len(edge_list)):
                    if edge_list[i][0] == v2:
                        return edge_list[i]
                return None
            else:
                return None
        else:
            raise ValueError('Node not in graph!')

    def out_edge(self, v):
        if self._valid(v):
            if v in self.edge:
                return self.edge[v]
            else:
                return []
        else:
            raise ValueError('Node not in graph!')

    def degree(self, v):
        if self._valid(v):
            if v in self.edge:
                return len(self.edge[v])
            else:
                return 0
        else:
            raise ValueError('Node not in graph!')

    def dfs_recursive(self, v):
        if self._valid(v):
            visited = set()
            result = []
            def helper(node):
                if node not in visited:
                    visited.add(node)
                    result.append(node)
                    node_edge_list = self.out_edge(node)
                    for edge in node_edge_list:
                        helper(edge[0])
            helper(v)
            rest = []
            for node in self.vertices():
                if node not in visited:
                    rest.append(node)
            if rest:
                rest.sort(key=lambda rest_node: len(self.out_edge(rest_node)), reverse=True)
            for rest_node in rest:
                helper(rest_node)
            return result
        else:
            raise ValueError('Node not in graph!')

    def dfs(self, v):
        if self._valid(v):
            visited = set()
            result = []
            rest = []
            def dfs(root):
                stack = [root]
                while stack:
                    node = stack.pop()
                    if node not in visited:
                        result.append(node)
                        visited.add(node)
                        node_edge_list = self.out_edge(node)
                        stack.append(node)
                        for edge in node_edge_list:
                            if edge[0] not in visited:
                                stack.append(edge[0])
            dfs(v)
            for node in self.vertices():
                if node not in visited:
                    rest.append(node)
            if rest:
                rest.sort(key=lambda rest_node: len(self.out_edge(rest_node)), reverse=True)
            for rest_node in rest:
                dfs(rest_node)
            return result
        else:
            raise ValueError('Node not in graph!')

    def bfs(self, v):
        if self._valid(v):
            visited = set()
            result = []
            rest = []
            def bfs(root):
                queue = [root]
                while queue:
                    node = queue.pop(0)
                    if node not in visited:
                        visited.add(node)
                        result.append(node)
                        node_edge_list = self.out_edge(node)
                        for edge in node_edge_list:
                            queue.append(edge[0])
            bfs(v)
            for node in self.vertices():
                if node not in visited:
                    rest.append(node)
            if rest:
                rest.sort(key=lambda rest_node: len(self.out_edge(rest_node)), reverse=True)
            for rest_node in rest:
                bfs(rest_node)
            return result
        else:
            raise ValueError('Node not in graph!')
