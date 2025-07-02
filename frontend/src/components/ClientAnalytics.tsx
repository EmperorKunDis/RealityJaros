
import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Users } from 'lucide-react';

const ClientAnalytics = () => {
  const clientData = [
    {
      name: 'TechCorp Solutions',
      category: 'Technologie',
      responseTime: '2.3h',
      satisfaction: 96,
      totalEmails: 247,
      frequency: 'Vysoká'
    },
    {
      name: 'Design Studio Alpha',
      category: 'Kreativní',
      responseTime: '1.8h',
      satisfaction: 94,
      totalEmails: 189,
      frequency: 'Střední'
    },
    {
      name: 'Financial Partners LLC',
      category: 'Finance',
      responseTime: '1.2h',
      satisfaction: 98,
      totalEmails: 156,
      frequency: 'Vysoká'
    },
    {
      name: 'Creative Agency Pro',
      category: 'Marketing',
      responseTime: '3.1h',
      satisfaction: 89,
      totalEmails: 134,
      frequency: 'Střední'
    },
    {
      name: 'Healthcare Innovations',
      category: 'Zdravotnictví',
      responseTime: '2.7h',
      satisfaction: 92,
      totalEmails: 98,
      frequency: 'Nízká'
    }
  ];

  const getCategoryColor = (category: string) => {
    const colors = {
      'Technologie': 'bg-cyber-500/20 text-cyber-300',
      'Kreativní': 'bg-purple-500/20 text-purple-300',
      'Finance': 'bg-green-500/20 text-green-300',
      'Marketing': 'bg-yellow-500/20 text-yellow-300',
      'Zdravotnictví': 'bg-blue-500/20 text-blue-300'
    };
    return colors[category as keyof typeof colors] || 'bg-gray-500/20 text-gray-300';
  };

  const getFrequencyColor = (frequency: string) => {
    switch (frequency) {
      case 'Vysoká': return 'bg-red-500/20 text-red-300';
      case 'Střední': return 'bg-yellow-500/20 text-yellow-300';
      case 'Nízká': return 'bg-green-500/20 text-green-300';
      default: return 'bg-gray-500/20 text-gray-300';
    }
  };

  return (
    <Card className="glass-card cyber-glow">
      <CardHeader>
        <CardTitle className="text-gradient flex items-center gap-2">
          <Users className="h-5 w-5" />
          Analýza klientských vztahů
        </CardTitle>
        <CardDescription>
          AI analýza vzorců komunikace s klienty
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {clientData.map((client, index) => (
            <motion.div
              key={client.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="p-4 bg-white/5 backdrop-blur-sm rounded-lg border border-white/10"
            >
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h4 className="font-medium text-cyber-200">{client.name}</h4>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="outline" className={getCategoryColor(client.category)}>
                      {client.category}
                    </Badge>
                    <Badge variant="outline" className={getFrequencyColor(client.frequency)}>
                      {client.frequency} frekvence
                    </Badge>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm text-muted-foreground">Průměrná odezva</p>
                  <p className="font-medium text-neon-300">{client.responseTime}</p>
                </div>
              </div>
              
              <div className="space-y-3">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-muted-foreground">Skóre spokojenosti</span>
                    <span className="text-sm font-medium text-cyber-300">{client.satisfaction}%</span>
                  </div>
                  <Progress value={client.satisfaction} className="h-2" />
                </div>
                
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Celkem emailů:</span>
                  <span className="text-foreground">{client.totalEmails}</span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export { ClientAnalytics };
