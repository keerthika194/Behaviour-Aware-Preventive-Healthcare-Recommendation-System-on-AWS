import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserAttribute,
  CognitoUserSession,
} from 'amazon-cognito-identity-js';

const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID || 'ap-south-1_EtqP8T35c';
const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID || '8ubr2bs69koakql1cpl85nc5b';

const poolData = {
  UserPoolId: userPoolId,
  ClientId: clientId,
};

export const userPool = new CognitoUserPool(poolData);

export interface UserSessionData {
  username: string;
  email?: string;
  jwtToken: string;
  idToken: string;
  userSub?: string;
}

/**
 * Sign in existing user using Cognito User Pool
 */
export const signInUser = (username: string, password: string): Promise<UserSessionData> => {
  return new Promise((resolve, reject) => {
    const authenticationData = {
      Username: username,
      Password: password,
    };
    const authenticationDetails = new AuthenticationDetails(authenticationData);

    const userData = {
      Username: username,
      Pool: userPool,
    };
    const cognitoUser = new CognitoUser(userData);

    cognitoUser.authenticateUser(authenticationDetails, {
      onSuccess: (session: CognitoUserSession) => {
        const idToken = session.getIdToken().getJwtToken();
        const accessToken = session.getAccessToken().getJwtToken();
        const payload = session.getIdToken().decodePayload();
        
        resolve({
          username: cognitoUser.getUsername(),
          email: payload.email || username,
          jwtToken: idToken,
          idToken: idToken,
          userSub: payload.sub,
        });
      },
      onFailure: (err) => {
        reject(err);
      },
      newPasswordRequired: (userAttributes) => {
        delete userAttributes.email_verified;
        cognitoUser.completeNewPasswordChallenge(password, userAttributes, {
          onSuccess: (session) => {
            const idToken = session.getIdToken().getJwtToken();
            const payload = session.getIdToken().decodePayload();
            resolve({
              username: cognitoUser.getUsername(),
              email: payload.email || username,
              jwtToken: idToken,
              idToken: idToken,
              userSub: payload.sub,
            });
          },
          onFailure: (err) => reject(err),
        });
      },
    });
  });
};

/**
 * Sign up new user
 */
export const signUpUser = (username: string, email: string, password: string): Promise<any> => {
  return new Promise((resolve, reject) => {
    const attributeList = [
      new CognitoUserAttribute({
        Name: 'email',
        Value: email,
      }),
    ];

    userPool.signUp(username, password, attributeList, [], (err, result) => {
      if (err) {
        reject(err);
        return;
      }
      resolve(result);
    });
  });
};

/**
 * Confirm Sign Up code
 */
export const confirmSignUpUser = (username: string, code: string): Promise<any> => {
  return new Promise((resolve, reject) => {
    const userData = {
      Username: username,
      Pool: userPool,
    };
    const cognitoUser = new CognitoUser(userData);

    cognitoUser.confirmRegistration(code, true, (err, result) => {
      if (err) {
        reject(err);
        return;
      }
      resolve(result);
    });
  });
};

/**
 * Sign out current authenticated user
 */
export const signOutUser = (): void => {
  const cognitoUser = userPool.getCurrentUser();
  if (cognitoUser) {
    cognitoUser.signOut();
  }
  localStorage.removeItem('auth_session');
};

/**
 * Get current session token asynchronously
 */
export const getCurrentSession = (): Promise<UserSessionData | null> => {
  return new Promise((resolve) => {
    const cognitoUser = userPool.getCurrentUser();
    if (!cognitoUser) {
      // Check fallback cached session
      const cached = localStorage.getItem('auth_session');
      if (cached) {
        try {
          const parsed = JSON.parse(cached);
          resolve(parsed);
          return;
        } catch {
          resolve(null);
          return;
        }
      }
      resolve(null);
      return;
    }

    cognitoUser.getSession((err: any, session: CognitoUserSession) => {
      if (err || !session.isValid()) {
        resolve(null);
        return;
      }

      const idToken = session.getIdToken().getJwtToken();
      const payload = session.getIdToken().decodePayload();
      const sessionData: UserSessionData = {
        username: cognitoUser.getUsername(),
        email: payload.email || cognitoUser.getUsername(),
        jwtToken: idToken,
        idToken: idToken,
        userSub: payload.sub,
      };
      localStorage.setItem('auth_session', JSON.stringify(sessionData));
      resolve(sessionData);
    });
  });
};
