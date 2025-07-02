
import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Mail, MailOpen, Loader2, Star, StarOff } from 'lucide-react';
import { useEmails, useMarkEmailRead, useStarEmail, useAnalyzeEmail } from '../hooks/useEmails';
import { useAuth } from '../contexts/AuthContext';

const EmailPreview = () => {
  const { user } = useAuth();
  const { data: emailsData, isLoading, error } = useEmails({ pageSize: 10 });
  const { markAsRead, isLoading: markingRead } = useMarkEmailRead();
  const { star, unstar, isLoading: starring } = useStarEmail();
  const analyzeEmail = useAnalyzeEmail();

  const handleMarkAsRead = (emailId: string) => {
    markAsRead(emailId);
  };

  const handleToggleStar = (email: any) => {
    if (email.is_starred) {
      unstar(email.id);
    } else {
      star(email.id);
    }
  };

  const handleAnalyzeEmail = (emailId: string) => {
    if (user?.id) {
      analyzeEmail.mutate({
        emailId,
        userId: user.id,
        priority: 'normal'
      });
    }
  };

  const formatTimeAgo = (dateString: string) => {
    const now = new Date();
    const date = new Date(dateString);
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'právě teď';
    if (diffInMinutes < 60) return `před ${diffInMinutes} minutami`;
    
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `před ${diffInHours} hodinami`;
    
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 7) return `před ${diffInDays} dny`;
    
    return date.toLocaleDateString('cs-CZ');
  };

  const emails = emailsData?.emails || [];

  const getPriorityColor = (urgency: string | null) => {
    switch (urgency) {
      case 'high': return 'bg-red-500/20 text-red-300 border-red-500/30';
      case 'medium': return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
      case 'low': return 'bg-green-500/20 text-green-300 border-green-500/30';
      default: return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
    }
  };

  const getPriorityText = (urgency: string | null) => {
    switch (urgency) {
      case 'high': return 'vysoká';
      case 'medium': return 'střední';
      case 'low': return 'nízká';
      default: return 'neurčená';
    }
  };

  const getStatusColor = (email: any) => {
    if (!email.is_read) return 'bg-cyber-500/20 text-cyber-300 border-cyber-500/30';
    if (email.is_analyzed) return 'bg-neon-500/20 text-neon-300 border-neon-500/30';
    if (email.is_processed) return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
    return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
  };

  const getStatusText = (email: any) => {
    if (!email.is_read) return 'nepřečtený';
    if (email.is_analyzed) return 'analyzován';
    if (email.is_processed) return 'zpracován';
    return 'přečtený';
  };

  return (
    <Card className="glass-card cyber-glow">
      <CardHeader>
        <CardTitle className="text-gradient flex items-center gap-2">
          <Mail className="h-5 w-5" />
          Příchozí emaily
        </CardTitle>
        <CardDescription>
          AI analýza emailů a generování odpovědí
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="p-4 bg-white/5 backdrop-blur-sm rounded-lg border border-white/10">
                <div className="animate-pulse">
                  <div className="flex items-start gap-4">
                    <div className="h-10 w-10 bg-white/10 rounded-full"></div>
                    <div className="flex-1">
                      <div className="h-4 bg-white/10 rounded w-1/4 mb-2"></div>
                      <div className="h-3 bg-white/10 rounded w-1/6 mb-3"></div>
                      <div className="h-4 bg-white/10 rounded w-3/4 mb-2"></div>
                      <div className="h-3 bg-white/10 rounded w-full"></div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="text-center py-8 text-red-400">
            <Mail className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Chyba při načítání emailů</p>
            <p className="text-sm text-muted-foreground mt-1">Zkuste obnovit stránku</p>
          </div>
        ) : emails.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Mail className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Žádné emaily k zobrazení</p>
            <p className="text-sm">Nové emaily se zobrazí zde automaticky</p>
          </div>
        ) : (
          <div className="space-y-4">
            {emails.map((email, index) => (
              <motion.div
                key={email.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`p-4 bg-white/5 backdrop-blur-sm rounded-lg border transition-all group ${
                  email.is_read ? 'border-white/10 hover:border-cyber-500/30' : 'border-cyber-500/30 bg-cyber-500/5'
                }`}
              >
                <div className="flex items-start gap-4">
                  <Avatar className="h-10 w-10">
                    <AvatarFallback className="bg-gradient-to-r from-cyber-500 to-neon-500 text-white">
                      {email.sender.split('@')[0].slice(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <p className="font-medium text-cyber-200">{email.sender}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatTimeAgo(email.received_datetime || email.sent_datetime)}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 w-6 p-0"
                          onClick={() => handleToggleStar(email)}
                          disabled={starring}
                        >
                          {email.is_starred ? (
                            <Star className="h-3 w-3 text-yellow-400 fill-yellow-400" />
                          ) : (
                            <StarOff className="h-3 w-3 text-muted-foreground" />
                          )}
                        </Button>
                        <Badge variant="outline" className={getPriorityColor(email.urgency_level)}>
                          {getPriorityText(email.urgency_level)}
                        </Badge>
                        <Badge variant="outline" className={getStatusColor(email)}>
                          {getStatusText(email)}
                        </Badge>
                      </div>
                    </div>
                    
                    <h4 className="font-medium text-foreground mb-1">{email.subject || 'Bez předmětu'}</h4>
                    <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                      {email.body_text?.substring(0, 150) || 'Náhled textu není k dispozici'}...
                    </p>
                    
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        {email.sentiment_score && (
                          <span className="text-xs text-neon-400">
                            Sentiment: {Math.round(email.sentiment_score * 100)}%
                          </span>
                        )}
                        {email.has_attachments && (
                          <Badge variant="outline" className="text-xs">
                            📎 Přílohy
                          </Badge>
                        )}
                      </div>
                      
                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        {!email.is_read && (
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="h-8 text-xs"
                            onClick={() => handleMarkAsRead(email.id)}
                            disabled={markingRead}
                          >
                            <MailOpen className="h-3 w-3 mr-1" />
                            Označit jako přečtený
                          </Button>
                        )}
                        <Button 
                          size="sm" 
                          className="h-8 text-xs bg-gradient-to-r from-cyber-500 to-neon-500"
                          onClick={() => handleAnalyzeEmail(email.id)}
                          disabled={analyzeEmail.isPending}
                        >
                          {analyzeEmail.isPending ? (
                            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          ) : (
                            <>Analyzovat</>
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { EmailPreview };
