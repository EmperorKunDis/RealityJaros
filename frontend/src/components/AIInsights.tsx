
import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Settings } from 'lucide-react';

const AIInsights = () => {
  const systemMetrics = [
    { label: 'Vektorová databáze', value: 98, status: 'Optimální' },
    { label: 'RAG Engine', value: 96, status: 'Vynikající' },
    { label: 'Analýza stylu', value: 94, status: 'Aktivní' },
    { label: 'Kvalita odpovědí', value: 97, status: 'Špičková' }
  ];

  const recentUpdates = [
    {
      title: 'Vylepšená kategorizace klientů',
      description: 'Zlepšena přesnost klasifikace typu podnikání o 12%',
      time: 'před 2 hodinami',
      type: 'vylepšení'
    },
    {
      title: 'Nové vzory stylu psaní',
      description: 'Detekováno 15 nových komunikačních vzorů napříč klienty',
      time: 'před 6 hodinami',
      type: 'objev'
    },
    {
      title: 'Optimalizace vektorové databáze',
      description: 'Snížena latence vyhledávání podobnosti o 25%',
      time: 'před 1 dnem',
      type: 'výkon'
    }
  ];

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'vylepšení': return 'bg-green-500/20 text-green-300';
      case 'objev': return 'bg-cyber-500/20 text-cyber-300';
      case 'výkon': return 'bg-neon-500/20 text-neon-300';
      default: return 'bg-gray-500/20 text-gray-300';
    }
  };

  return (
    <div className="space-y-6">
      {/* System Performance */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.6 }}
      >
        <Card className="glass-card cyber-glow">
          <CardHeader>
            <CardTitle className="text-gradient flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Výkon AI systému
            </CardTitle>
            <CardDescription>
              Monitorování AI komponent v reálném čase
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {systemMetrics.map((metric, index) => (
                <motion.div
                  key={metric.label}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-cyber-200">{metric.label}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="bg-green-500/20 text-green-300 border-green-500/30">
                        {metric.status}
                      </Badge>
                      <span className="text-sm text-neon-300">{metric.value}%</span>
                    </div>
                  </div>
                  <Progress value={metric.value} className="h-2" />
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Recent AI Updates */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
      >
        <Card className="glass-card cyber-glow">
          <CardHeader>
            <CardTitle className="text-gradient">Aktualizace AI učení</CardTitle>
            <CardDescription>
              Nejnovější vylepšení a objevy
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentUpdates.map((update, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="p-3 bg-white/5 backdrop-blur-sm rounded-lg border border-white/10"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="font-medium text-cyber-200 text-sm">{update.title}</h4>
                    <Badge variant="outline" className={getTypeColor(update.type)}>
                      {update.type}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mb-2">{update.description}</p>
                  <span className="text-xs text-muted-foreground">{update.time}</span>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Technology Stack */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
      >
        <Card className="glass-card cyber-glow">
          <CardHeader>
            <CardTitle className="text-gradient">Technologický stack</CardTitle>
            <CardDescription>
              Pohání vaši emailovou automatizaci
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              {[
                'FastAPI', 'OpenAI GPT-4', 'ChromaDB', 'LangChain',
                'PostgreSQL', 'Vector Search', 'RAG Engine', 'OAuth 2.0'
              ].map((tech, index) => (
                <motion.div
                  key={tech}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.05 }}
                  className="p-2 bg-gradient-to-r from-cyber-500/10 to-neon-500/10 rounded-lg border border-cyber-500/20 text-center"
                >
                  <span className="text-xs text-cyber-300 font-medium">{tech}</span>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
};

export { AIInsights };
