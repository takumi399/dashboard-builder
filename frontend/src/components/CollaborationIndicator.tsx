import React from 'react';
import { Avatar, Badge, Tooltip } from 'antd';
import { TeamOutlined } from '@ant-design/icons';

interface OnlineUser {
  user_id: number;
  username: string;
}

const AVATAR_COLORS = [
  '#f56a00',
  '#7265e6',
  '#ffbf00',
  '#00a2ae',
  '#87d068',
  '#108ee9',
  '#f5222d',
  '#722ed1',
];

interface CollaborationIndicatorProps {
  onlineUsers: OnlineUser[];
  isConnected: boolean;
}

/**
 * 协作指示器 — 显示在线人数和用户头像
 *
 * 放在 DashboardEditorPage 顶部工具栏
 */
const CollaborationIndicator: React.FC<CollaborationIndicatorProps> = ({
  onlineUsers,
  isConnected,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '2px 8px',
        borderRadius: 6,
        background: isConnected ? '#f6ffed' : '#fff2f0',
        border: `1px solid ${isConnected ? '#b7eb8f' : '#ffccc7'}`,
        transition: 'background 0.3s, border-color 0.3s',
      }}
    >
      <Badge
        status={isConnected ? 'success' : 'error'}
        text=""
        style={{ marginRight: -4 }}
      />
      <TeamOutlined
        style={{ color: isConnected ? '#52c41a' : '#ff4d4f', fontSize: 16 }}
      />
      <span
        style={{
          fontSize: 13,
          color: isConnected ? '#389e0d' : '#cf1322',
          whiteSpace: 'nowrap',
        }}
      >
        {onlineUsers.length} 人在线
      </span>
      {onlineUsers.length > 0 && (
        <Avatar.Group
          maxCount={4}
          size="small"
          maxStyle={{ cursor: 'pointer' }}
        >
          {onlineUsers.map((user, index) => (
            <Tooltip key={user.user_id} title={user.username}>
              <Avatar
                style={{
                  backgroundColor:
                    AVATAR_COLORS[index % AVATAR_COLORS.length],
                  fontSize: 11,
                  cursor: 'default',
                }}
                size={28}
              >
                {user.username.charAt(0).toUpperCase()}
              </Avatar>
            </Tooltip>
          ))}
        </Avatar.Group>
      )}
    </div>
  );
};

export default CollaborationIndicator;
