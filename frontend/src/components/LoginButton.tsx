/**
 * Login Button Component for Google OAuth Authentication
 */

import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, Mail } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { motion } from 'framer-motion';

const LoginButton: React.FC = () => {
  const { login, isLoading, error, clearError } = useAuth();

  const handleLogin = async () => {
    if (error) clearError();
    await login();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="min-h-screen flex items-center justify-center p-6"
    >
      <Card className="glass-card cyber-glow max-w-md w-full">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-gradient-to-r from-cyber-400 to-neon-400 flex items-center justify-center">
            <Mail className="h-6 w-6 text-white" />
          </div>
          <CardTitle className="text-gradient text-2xl">
            AI Emailový Asistent
          </CardTitle>
          <CardDescription className="text-base">
            Přihlaste se pomocí Google účtu pro přístup k inteligentní automatizaci emailů
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm"
            >
              {error}
            </motion.div>
          )}
          
          <Button
            onClick={handleLogin}
            disabled={isLoading}
            className="w-full bg-gradient-to-r from-cyber-600 to-neon-600 hover:from-cyber-700 hover:to-neon-700 text-white border-0"
            size="lg"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Přihlašování...
              </>
            ) : (
              <>
                <Mail className="mr-2 h-4 w-4" />
                Přihlásit se pomocí Google
              </>
            )}
          </Button>
          
          <div className="text-center text-xs text-muted-foreground">
            <p>Připojením souhlasíte s našimi podmínkami použití</p>
            <p className="mt-1">Vaše data jsou v bezpečí a chráněna</p>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
};

export default LoginButton;