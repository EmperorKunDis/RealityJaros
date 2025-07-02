
import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Mail, MailOpen, Users, Settings } from 'lucide-react';

const StatsGrid = () => {
  const stats = [
    {
      title: 'Celkem zpracovaných emailů',
      value: '12,847',
      change: '+23.5%',
      icon: Mail,
      gradient: 'from-cyber-500 to-cyber-600'
    },
    {
      title: 'AI odpovědí vygenerováno',
      value: '3,924',
      change: '+18.2%',
      icon: MailOpen,
      gradient: 'from-neon-500 to-neon-600'
    },
    {
      title: 'Aktivní klienti',
      value: '247',
      change: '+12.8%',
      icon: Users,
      gradient: 'from-purple-500 to-purple-600'
    },
    {
      title: 'Efektivita systému',
      value: '96.4%',
      change: '+5.1%',
      icon: Settings,
      gradient: 'from-blue-500 to-blue-600'
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {stats.map((stat, index) => (
        <motion.div
          key={stat.title}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1, duration: 0.6 }}
        >
          <Card className="glass-card cyber-glow group hover:scale-105 transition-all duration-300">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
              <div className={`p-2 rounded-lg bg-gradient-to-r ${stat.gradient} group-hover:shadow-neon transition-all`}>
                <stat.icon className="h-4 w-4 text-white" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-gradient mb-1">
                {stat.value}
              </div>
              <p className="text-xs text-green-400 flex items-center">
                <span className="mr-1">↗</span>
                {stat.change} oproti minulému měsíci
              </p>
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  );
};

export { StatsGrid };
