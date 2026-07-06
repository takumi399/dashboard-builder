"""
WebSocket 协作端点测试

测试 WebSocket 连接、广播转发、未授权拒绝。
使用 TestClient.websocket_connect() 测试同步 WebSocket 流程。
Token 直接通过 create_access_token 创建，无需数据库依赖。
"""

import pytest
import json as json_mod
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token


class TestWebSocket:
    """WebSocket 端点单元测试"""

    def test_websocket_unauthorized_no_token(self):
        """无 token 连接应被拒绝。"""
        client = TestClient(app)
        # 服务端关闭连接时 client 端会收到异常
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/dashboards/1") as ws:
                ws.receive_json()

    def test_websocket_unauthorized_invalid_token(self):
        """无效 token 连接应被拒绝。"""
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect(
                "/ws/dashboards/1?token=invalid.token.here"
            ) as ws:
                ws.receive_json()

    def test_websocket_connect(self):
        """有效 token 应成功连接并接收在线用户列表。"""
        token = create_access_token(
            data={"sub": "1", "username": "testuser"}
        )
        client = TestClient(app)

        with client.websocket_connect(
            f"/ws/dashboards/1?token={token}"
        ) as ws:
            # 第一条消息应为 online_users
            msg = ws.receive_json()
            assert msg["type"] == "online_users"
            assert len(msg["users"]) == 1
            assert msg["users"][0]["user_id"] == 1
            assert msg["users"][0]["username"] == "testuser"

    def test_websocket_broadcast_join_leave(self):
        """测试用户加入/离开广播。"""
        token1 = create_access_token(
            data={"sub": "1", "username": "user1"}
        )
        token2 = create_access_token(
            data={"sub": "2", "username": "user2"}
        )
        client = TestClient(app)

        # 用户 1 连接
        with client.websocket_connect(
            f"/ws/dashboards/1?token={token1}"
        ) as ws1:
            # ws1 收到 online_users（只有自己）
            msg = ws1.receive_json()
            assert msg["type"] == "online_users"
            assert len(msg["users"]) == 1

            # 用户 2 连接同一看板
            with client.websocket_connect(
                f"/ws/dashboards/1?token={token2}"
            ) as ws2:
                # ws2 收到 online_users（两个用户）
                msg = ws2.receive_json()
                assert msg["type"] == "online_users"
                assert len(msg["users"]) == 2

                # ws1 收到 user_joined（用户 2 加入）
                msg = ws1.receive_json()
                assert msg["type"] == "user_joined"
                assert msg["user_id"] == 2
                assert msg["username"] == "user2"

            # ws2 退出作用域 → 断开
            # ws1 应收到 user_left
            msg = ws1.receive_json()
            assert msg["type"] == "user_left"
            assert msg["user_id"] == 2

    def test_websocket_broadcast_operation(self):
        """一个客户端发送操作，其他客户端收到广播。"""
        token1 = create_access_token(
            data={"sub": "1", "username": "user1"}
        )
        token2 = create_access_token(
            data={"sub": "2", "username": "user2"}
        )
        client = TestClient(app)

        with client.websocket_connect(
            f"/ws/dashboards/1?token={token1}"
        ) as ws1:
            ws1.receive_json()  # 消费 online_users

            with client.websocket_connect(
                f"/ws/dashboards/1?token={token2}"
            ) as ws2:
                ws2.receive_json()  # 消费 online_users
                ws1.receive_json()  # 消费 user_joined

                # ws1 发送 chart_moved 操作
                operation = {
                    "type": "chart_moved",
                    "chart_id": 42,
                    "position_x": 150,
                    "position_y": 300,
                }
                ws1.send_json(operation)

                # ws2 应收到广播转发的操作
                msg = ws2.receive_json()
                assert msg["type"] == "chart_moved"
                assert msg["chart_id"] == 42
                assert msg["position_x"] == 150
                assert msg["position_y"] == 300

                # ws1 不应收到自己发送的消息
                ws1.send_json({"type": "ping"})
                msg = ws2.receive_json()
                assert msg["type"] == "ping"

    def test_websocket_multiple_operation_types(self):
        """测试各种操作类型的广播转发。"""
        token1 = create_access_token(
            data={"sub": "1", "username": "user1"}
        )
        token2 = create_access_token(
            data={"sub": "2", "username": "user2"}
        )
        client = TestClient(app)

        operations = [
            {
                "type": "chart_added",
                "chart_id": 1,
                "chart_type": "bar",
                "title": "New Chart",
            },
            {
                "type": "chart_resized",
                "chart_id": 1,
                "width": 500,
                "height": 400,
            },
            {
                "type": "chart_updated",
                "chart_id": 1,
                "title": "Updated Chart",
            },
            {
                "type": "chart_deleted",
                "chart_id": 1,
            },
        ]

        for operation in operations:
            with client.websocket_connect(
                f"/ws/dashboards/1?token={token1}"
            ) as ws1:
                ws1.receive_json()  # online_users

                with client.websocket_connect(
                    f"/ws/dashboards/1?token={token2}"
                ) as ws2:
                    ws2.receive_json()  # online_users
                    ws1.receive_json()  # user_joined

                    ws1.send_json(operation)
                    msg = ws2.receive_json()
                    assert msg["type"] == operation["type"]
                    # 验证所有字段都被正确转发
                    for key, value in operation.items():
                        assert msg[key] == value
