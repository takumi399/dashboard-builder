import { useState, useEffect, useRef, useCallback } from 'react';

export interface OnlineUser {
  user_id: number;
  username: string;
}

export interface WsMessage {
  type: string;
  [key: string]: unknown;
}

type MessageHandler = (msg: WsMessage) => void;

const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY_MS = 3000;

/**
 * WebSocket 协作 Hook
 *
 * 连接 ws://localhost:8000/ws/dashboards/{dashboardId}?token={token}
 * 自动重连（断开后 3 秒重试，最多 5 次）
 *
 * @returns isConnected - 连接状态
 * @returns onlineUsers - 在线用户列表
 * @returns sendOperation - 发送操作消息
 * @returns onMessage - 注册消息回调（返回 unsubscribe 函数）
 */
export function useWebSocket(dashboardId: string | undefined, token: string | null) {
  const [isConnected, setIsConnected] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState<OnlineUser[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const messageHandlersRef = useRef<MessageHandler[]>([]);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!token || !dashboardId || !mountedRef.current) return;

    // 清除已有的重连计时器
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    const wsUrl = `ws://localhost:8000/ws/dashboards/${dashboardId}?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) {
        ws.close();
        return;
      }
      setIsConnected(true);
      reconnectCountRef.current = 0;
    };

    ws.onmessage = (event: MessageEvent) => {
      if (!mountedRef.current) return;
      try {
        const msg: WsMessage = JSON.parse(event.data as string);

        // 处理系统消息
        switch (msg.type) {
          case 'online_users':
            setOnlineUsers((msg.users as OnlineUser[]) || []);
            break;
          case 'user_joined':
            setOnlineUsers((prev) => {
              const filtered = prev.filter((u) => u.user_id !== msg.user_id);
              return [
                ...filtered,
                {
                  user_id: msg.user_id as number,
                  username: msg.username as string,
                },
              ];
            });
            break;
          case 'user_left':
            setOnlineUsers((prev) =>
              prev.filter((u) => u.user_id !== msg.user_id)
            );
            break;
        }

        // 分发给业务层处理器
        messageHandlersRef.current.forEach((handler) => {
          try {
            handler(msg);
          } catch {
            // 忽略单个 handler 的错误
          }
        });
      } catch {
        // 忽略 JSON 解析错误
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setIsConnected(false);
      setOnlineUsers([]);

      // 自动重连
      if (reconnectCountRef.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectCountRef.current++;
        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, RECONNECT_DELAY_MS);
      }
    };

    ws.onerror = () => {
      // onclose 会在 onerror 之后自动触发，重连逻辑在 onclose 中处理
      ws.close();
    };
  }, [dashboardId, token]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  /** 发送操作消息到房间内其他用户 */
  const sendOperation = useCallback((operation: WsMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(operation));
    }
  }, []);

  /** 注册消息回调，返回取消订阅函数 */
  const onMessage = useCallback((handler: MessageHandler) => {
    messageHandlersRef.current.push(handler);
    return () => {
      messageHandlersRef.current = messageHandlersRef.current.filter(
        (h) => h !== handler
      );
    };
  }, []);

  return { isConnected, onlineUsers, sendOperation, onMessage };
}
