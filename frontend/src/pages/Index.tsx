
import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import Dashboard from '../components/Dashboard';
import LoginButton from '../components/LoginButton';
import { Loader2 } from 'lucide-react';

const Index = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-cyber-400" />
          <p className="text-muted-foreground">Načítání...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginButton />;
  }

  return <Dashboard />;
};

export default Index;
