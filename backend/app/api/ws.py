"""
WebSocket 实时协作端点

维护内存中的房间字典 {dashboard_id: {WebSocket: user_info}}
支持用户加入/离开广播、操作转发、在线用户列表。
"""

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.security import decode_access_token

router = APIRouter()


class RoomManager:
    """管理 WebSocket 会议室：加入/离开/广播，asyncio.Lock 保护并发访问。"""

    def __init__(self):
        self._rooms: dict[int, dict[WebSocket, dict]] = {}
        self._lock = asyncio.Lock()

    async def join(
        self, dashboard_id: int, websocket: WebSocket,
        user_id: int, username: str
    ) -> None:
        """用户加入房间：注册连接、发送在线列表、广播加入消息。"""
        async with self._lock:
            if dashboard_id not in self._rooms:
                self._rooms[dashboard_id] = {}
            self._rooms[dashboard_id][websocket] = {
                "user_id": user_id,
                "username": username,
            }

        # 向新用户发送当前在线列表
        users = self.get_online_users(dashboard_id)
        await websocket.send_json({"type": "online_users", "users": users})

        # 广播用户加入消息给其他人
        await self.broadcast(
            dashboard_id,
            {"type": "user_joined", "user_id": user_id, "username": username},
            exclude=websocket,
        )

    async def leave(self, dashboard_id: int, websocket: WebSocket) -> None:
        """用户离开房间：移除连接、广播离开消息。"""
        user_info = None
        async with self._lock:
            if dashboard_id in self._rooms:
                user_info = self._rooms[dashboard_id].pop(websocket, None)
                if not self._rooms[dashboard_id]:
                    del self._rooms[dashboard_id]

        if user_info:
            await self.broadcast(
                dashboard_id,
                {"type": "user_left", "user_id": user_info["user_id"]},
            )

    def get_online_users(self, dashboard_id: int) -> list[dict]:
        """获取指定房间的在线用户列表（不含锁，调用方自行保护）。"""
        if dashboard_id not in self._rooms:
            return []
        return [
            {"user_id": info["user_id"], "username": info["username"]}
            for info in self._rooms[dashboard_id].values()
        ]

    async def broadcast(
        self, dashboard_id: int, message: dict, exclude: WebSocket | None = None
    ) -> None:
        """向房间内所有用户广播消息（可选排除某个连接）。"""
        # 复制连接列表后释放锁，避免在 send 时持有锁
        async with self._lock:
            if dashboard_id not in self._rooms:
                return
            targets = list(self._rooms[dashboard_id].items())

        disconnected: list[WebSocket] = []
        for ws, _info in targets:
            if ws == exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        # 清理已断开的连接
        if disconnected:
            async with self._lock:
                if dashboard_id in self._rooms:
                    for ws in disconnected:
                        self._rooms[dashboard_id].pop(ws, None)
                    if not self._rooms[dashboard_id]:
                        del self._rooms[dashboard_id]


# 全局单例
manager = RoomManager()


@router.websocket("/ws/dashboards/{dashboard_id}")
async def websocket_endpoint(websocket: WebSocket, dashboard_id: int):
    """WebSocket 协作端点 —— 实时同步图表操作。

    查询参数:
        token: JWT access token

    支持的操作类型（广播转发）:
        chart_added, chart_moved, chart_resized, chart_deleted, chart_updated
    """
    # ── JWT 验证 ──
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = int(payload.get("sub", 0))
    username = payload.get("username", f"user_{user_id}")

    if user_id == 0:
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    # ── 建立连接 ──
    await websocket.accept()
    await manager.join(dashboard_id, websocket, user_id, username)

    try:
        while True:
            data = await websocket.receive_json()
            # 转发操作给房间内其他用户
            await manager.broadcast(dashboard_id, data, exclude=websocket)
    except WebSocketDisconnect:
        pass  # 正常的断开
    except Exception:
        pass  # 异常断开（如 JSON 解析失败）
    finally:
        await manager.leave(dashboard_id, websocket)
