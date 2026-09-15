import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  signInUser,
  signUpUser,
  confirmSignUpUser,
  signOutUser,
  getCurrentSession,
  UserSessionData,
} from '../services/cognito';

interface AuthContextType {
  user: UserSessionData | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  signup: (username: string, email: string, password: string) => Promise<any>;
  confirmCode: (username: string, code: string) => Promise<void>;
  demoLogin: (username?: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserSessionData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const session = await getCurrentSession();
        setUser(session);
      } catch (err) {
        console.error('Session initialization error:', err);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };
    initAuth();
  }, []);

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const session = await signInUser(username, password);
      setUser(session);
      localStorage.setItem('auth_session', JSON.stringify(session));
    } catch (err) {
      setIsLoading(false);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (username: string, email: string, password: string) => {
    return await signUpUser(username, email, password);
  };

  const confirmCode = async (username: string, code: string) => {
    await confirmSignUpUser(username, code);
  };

  const demoLogin = (username: string = 'demo_user_1600') => {
    const demoSession: UserSessionData = {
      username: username,
      email: `${username}@preventivehealth.org`,
      jwtToken: 'demo_jwt_token_sample',
      idToken: 'demo_id_token_sample',
      userSub: '1600',
    };
    setUser(demoSession);
    localStorage.setItem('auth_session', JSON.stringify(demoSession));
  };

  const logout = () => {
    signOutUser();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        signup,
        confirmCode,
        demoLogin,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
