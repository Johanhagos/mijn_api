import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';

type Props = { data: Array<{ date: string; amount: number }>; color?: string };

export default function RevenueChart({ data = [], color = '#228B22' }: Props) {
  return (
    <div style={{ width: '100%', height: 300 }} className="w-full">
      <ResponsiveContainer>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis 
            dataKey="date" 
            tick={{ fontSize: 12, fill: '#6b7280' }}
            stroke="#d1d5db"
          />
          <YAxis 
            tick={{ fontSize: 12, fill: '#6b7280' }}
            stroke="#d1d5db"
            tickFormatter={(v) => `€${v}`}
          />
          <Tooltip 
            formatter={(val: any) => [`€${new Intl.NumberFormat().format(Number(val))}`, 'Revenue']}
            contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
          />
          <Line 
            type="monotone" 
            dataKey="amount" 
            stroke={color} 
            strokeWidth={2} 
            dot={{ fill: color, r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
