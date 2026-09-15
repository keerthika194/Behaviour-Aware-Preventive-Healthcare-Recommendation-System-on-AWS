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