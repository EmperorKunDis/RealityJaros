
import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Mail, 
  Users, 
  Settings, 
  Bell,
  MailOpen,
  MailPlus
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useResponses } from '../hooks/useResponses';
import { StatsGrid } from './StatsGrid';
import { EmailPreview } from './EmailPreview';
import { ClientAnalytics } from './ClientAnalytics';
import { AIInsights } from './AIInsights';

const Dashboard = () => {
  const { user, isAuthenticated } = useAuth();
  const { data: responsesData, isLoading: responsesLoading } = useResponses({ 
    status: 'ready',
    pageSize: 10 
  });

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="glass-card cyber-glow max-w-md">
          <CardHeader>
            <CardTitle className="text-gradient">Authentication Required</CardTitle>
            <CardDescription>Please log in to access the dashboard</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6 space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-4xl font-bold text-gradient mb-2">
            AI Emailový Asistent
          </h1>
          <p className="text-muted-foreground text-lg">
            Inteligentní automatizace poháněná pokročilou RAG technologií
          </p>
          {user && (
            <p className="text-sm text-muted-foreground mt-1">
              Vítejte zpět, {user.display_name || user.email}
            </p>
          )}
        </div>
        <div className="flex items-center gap-4">
          <Badge variant="outline" className="glass-card text-cyber-300 border-cyber-500/30">
            🟢 Systém aktivní
          </Badge>
          <Button variant="outline" size="icon" className="glass-card hover:cyber-glow">
            <Bell className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" className="glass-card hover:cyber-glow">
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </motion.div>

      {/* Stats Grid */}
      <StatsGrid />

      {/* Main Content */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left Column - Email Management */}
        <div className="lg:col-span-2 space-y-6">
          <Tabs defaultValue="emails" className="w-full">
            <TabsList className="glass-card mb-6">
              <TabsTrigger value="emails" className="data-[state=active]:bg-cyber-600/50">
                <Mail className="h-4 w-4 mr-2" />
                Fronta emailů
              </TabsTrigger>
              <TabsTrigger value="responses" className="data-[state=active]:bg-cyber-600/50">
                <MailPlus className="h-4 w-4 mr-2" />
                AI Odpovědi
              </TabsTrigger>
              <TabsTrigger value="analytics" className="data-[state=active]:bg-cyber-600/50">
                <Users className="h-4 w-4 mr-2" />
                Analýza klientů
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="emails">
              <EmailPreview />
            </TabsContent>
            
            <TabsContent value="responses">
              <Card className="glass-card cyber-glow">
                <CardHeader>
                  <CardTitle className="text-gradient">Vygenerované odpovědi</CardTitle>
                  <CardDescription>
                    AI odpovědi připravené k revizi
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {responsesLoading ? (
                    <div className="space-y-4">
                      {[1, 2, 3].map((i) => (
                        <div key={i} className="p-4 bg-white/5 backdrop-blur-sm rounded-lg border border-white/10">
                          <div className="animate-pulse">
                            <div className="h-4 bg-white/10 rounded w-3/4 mb-2"></div>
                            <div className="h-3 bg-white/10 rounded w-1/2 mb-2"></div>
                            <div className="h-2 bg-white/10 rounded w-full"></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : responsesData?.responses.length ? (
                    <div className="space-y-4">
                      {responsesData.responses.map((response, index) => (
                        <motion.div
                          key={response.id}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: index * 0.1 }}
                          className="p-4 bg-white/5 backdrop-blur-sm rounded-lg border border-white/10 hover:border-cyber-500/30 transition-all"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div>
                              <p className="font-medium text-cyber-200">
                                {response.response_type === 'professional' ? 'Profesionální odpověď' : 
                                 response.response_type === 'friendly' ? 'Přátelská odpověď' : 
                                 'AI Odpověď'}
                              </p>
                              <p className="text-sm text-muted-foreground">
                                {response.generated_response.substring(0, 60)}...
                              </p>
                            </div>
                            <Badge variant="secondary" className="bg-neon-600/20 text-neon-300">
                              {Math.round((response.confidence_score || 0) * 100)}% jistota
                            </Badge>
                          </div>
                          <Progress value={(response.confidence_score || 0) * 100} className="h-2" />
                        </motion.div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <MailPlus className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Žádné vygenerované odpovědi</p>
                      <p className="text-sm">AI odpovědi se zobrazí zde po jejich vygenerování</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="analytics">
              <ClientAnalytics />
            </TabsContent>
          </Tabs>
        </div>

        {/* Right Column - AI Insights */}
        <div className="space-y-6">
          <AIInsights />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
