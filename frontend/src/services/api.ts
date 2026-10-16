import { getCurrentSession } from './cognito';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  'https://sofhfh3jm8.execute-api.ap-south-1.amazonaws.com';

export interface RecommendationResponse {
  recommendation_text?: string;
  recommendation?: string;
  activity?: string;
  activity_confidence?: number;
  risk_score?: number | string;
  risk_band?: 'Low' | 'Medium' | 'High' | string;
  user_id?: string | number;
  subject_id?: string | number;
  timestamp?: string;
  created_at?: string;
  event_id?: string;
  recommendation_id?: string;
  recommendations?: string[];
  health_profile?: Record<string, any>;
  [key: string]: any;
}

/**
 * Helper to get authorization headers with Cognito JWT Token
 */
async function getAuthHeaders(): Promise<HeadersInit> {
  const session = await getCurrentSession();

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  if (session && session.jwtToken) {
    headers['Authorization'] = `Bearer ${session.jwtToken}`;
  }

  return headers;
}

/**
 * Fetch preventive healthcare recommendations for a user.
 *
 * GET /recommendations?user_id=<user_id>
 *
 * The backend returns an array of recommendation objects.
 */
export async function getRecommendations(
  userId: string | number
): Promise<RecommendationResponse[]> {
  try {
    // If running in local demo mode with Patient ID 1600, serve demo response without remote AWS auth
    if (String(userId) === '1600') {
      return [
        {
          recommendation_id: 'rec_demo_1600',
          user_id: '1600',
          subject_id: 1600,
          activity: 'Sitting',
          activity_confidence: 0.985,
          risk_score: 0.42,
          risk_band: 'Medium',
          recommendation:
            'Your preventive risk assessment indicates moderate risk. Avoid continuous prolonged sitting. Intercept sedentary periods with light stretching or walking.',
          recommendation_text:
            'Your preventive risk assessment indicates moderate risk. Avoid continuous prolonged sitting. Intercept sedentary periods with light stretching or walking.',
          recommendations: [
            'Your preventive risk assessment indicates moderate risk. Increase daily physical activity and monitor dietary habits.',
            'Incorporate structured cardiovascular exercises (such as brisk walking or cycling) at least 3-4 days per week.',
            'Avoid continuous prolonged sitting. Intercept sedentary periods with light stretching or walking.',
          ],
          timestamp: new Date().toISOString(),
          created_at: new Date().toISOString(),
        },
      ];
    }

    const headers = await getAuthHeaders();

    const url =
      `${API_BASE_URL}/recommendations?user_id=` +
      encodeURIComponent(String(userId));

    const response = await fetch(url, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error(
          'Your session has expired. Please sign in again.'
        );
      }

      throw new Error(
        `API Request failed with status ${response.status}`
      );
    }

    const data = await response.json();

    if (!Array.isArray(data)) {
      console.warn(
        'Unexpected recommendations response format:',
        data
      );

      return [];
    }

    return data as RecommendationResponse[];
  } catch (error: any) {
    console.warn('API Fetch Notice:', error?.message || error);
    throw error;
  }
}

/**
 * Request updated recommendations.
 *
 * POST /recommendations
 */
export async function createRecommendation(
  payload: Record<string, any>
): Promise<RecommendationResponse> {
  try {
    const headers = await getAuthHeaders();

    const url = `${API_BASE_URL}/recommendations`;

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error(
          'Your session has expired. Please sign in again.'
        );
      }

      throw new Error(
        `API Request failed with status ${response.status}`
      );
    }

    const data = await response.json();

    return data as RecommendationResponse;
  } catch (error: any) {
    console.warn('API Post Notice:', error?.message || error);
    throw error;
  }
}

/**
 * Fetch the authenticated user's health profile.
 *
 * GET /profile
 */
export async function getProfile(): Promise<Record<string, any>> {
  try {
    const session = await getCurrentSession();
    if (session?.userSub === '1600') {
      const cached = localStorage.getItem('demo_profile_1600');
      if (cached) {
        try {
          return JSON.parse(cached);
        } catch {}
      }
      return {
        user_id: '1600',
        HighBP: 0,
        HighChol: 0,
        CholCheck: 1,
        BMI: 25.0,
        Smoker: 0,
        Stroke: 0,
        HeartDiseaseorAttack: 0,
        PhysActivity: 1,
        Fruits: 1,
        Veggies: 1,
        HvyAlcoholConsump: 0,
        AnyHealthcare: 1,
        NoDocbcCost: 0,
        GenHlth: 2,
        MentHlth: 0,
        PhysHlth: 0,
        DiffWalk: 0,
        Sex: 1,
        Age: 5,
        Education: 5,
        Income: 6,
      };
    }

    const headers = await getAuthHeaders();

    const url = `${API_BASE_URL}/profile`;

    const response = await fetch(url, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error(
          'Your session has expired. Please sign in again.'
        );
      }

      throw new Error(
        `API Request failed with status ${response.status}`
      );
    }

    const data = await response.json();

    return data as Record<string, any>;
  } catch (error: any) {
    console.warn('API Profile Fetch Notice:', error?.message || error);
    throw error;
  }
}

/**
 * Create or update the authenticated user's health profile.
 *
 * POST /profile
 */
export async function saveProfile(
  profileData: Record<string, any>
): Promise<Record<string, any>> {
  try {
    const session = await getCurrentSession();
    if (session?.userSub === '1600') {
      localStorage.setItem('demo_profile_1600', JSON.stringify(profileData));
      return {
        message: 'Demo health profile saved successfully.',
        user_id: '1600',
        profile: profileData,
      };
    }

    const headers = await getAuthHeaders();

    const url = `${API_BASE_URL}/profile`;

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(profileData),
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error(
          'Your session has expired. Please sign in again.'
        );
      }

      throw new Error(
        `API Request failed with status ${response.status}`
      );
    }

    const data = await response.json();

    return data as Record<string, any>;
  } catch (error: any) {
    console.warn('API Profile Save Notice:', error?.message || error);
    throw error;
  }
}