import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Header } from '../components/layout/Header';
import { LoadingState } from '../components/common/LoadingState';
import { getProfile, saveProfile } from '../services/api';
import {
  HeartPulse,
  Shield,
  Save,
  CheckCircle2,
  AlertCircle,
  Activity,
  UserCheck,
} from 'lucide-react';

export interface HealthProfileForm {
  HighBP: number;
  HighChol: number;
  CholCheck: number;
  BMI: number;
  Smoker: number;
  Stroke: number;
  HeartDiseaseorAttack: number;
  PhysActivity: number;
  Fruits: number;
  Veggies: number;
  HvyAlcoholConsump: number;
  AnyHealthcare: number;
  NoDocbcCost: number;
  GenHlth: number;
  MentHlth: number;
  PhysHlth: number;
  DiffWalk: number;
  Sex: number;
  Age: number;
  Education: number;
  Income: number;
}

const defaultProfile: HealthProfileForm = {
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

export const ProfilePage: React.FC = () => {
  const { user } = useAuth();
  const [formData, setFormData] = useState<HealthProfileForm>(defaultProfile);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [successMsg, setSuccessMsg] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string>('');

  useEffect(() => {
    const loadProfileData = async () => {
      setLoading(true);
      setErrorMsg('');
      try {
        const res = await getProfile();
        if (res && typeof res === 'object' && Object.keys(res).length > 0) {
          setFormData({
            HighBP: Number(res.HighBP ?? defaultProfile.HighBP),
            HighChol: Number(res.HighChol ?? defaultProfile.HighChol),
            CholCheck: Number(res.CholCheck ?? defaultProfile.CholCheck),
            BMI: Number(res.BMI ?? defaultProfile.BMI),
            Smoker: Number(res.Smoker ?? defaultProfile.Smoker),
            Stroke: Number(res.Stroke ?? defaultProfile.Stroke),
            HeartDiseaseorAttack: Number(res.HeartDiseaseorAttack ?? defaultProfile.HeartDiseaseorAttack),
            PhysActivity: Number(res.PhysActivity ?? defaultProfile.PhysActivity),
            Fruits: Number(res.Fruits ?? defaultProfile.Fruits),
            Veggies: Number(res.Veggies ?? defaultProfile.Veggies),
            HvyAlcoholConsump: Number(res.HvyAlcoholConsump ?? defaultProfile.HvyAlcoholConsump),
            AnyHealthcare: Number(res.AnyHealthcare ?? defaultProfile.AnyHealthcare),
            NoDocbcCost: Number(res.NoDocbcCost ?? defaultProfile.NoDocbcCost),
            GenHlth: Number(res.GenHlth ?? defaultProfile.GenHlth),
            MentHlth: Number(res.MentHlth ?? defaultProfile.MentHlth),
            PhysHlth: Number(res.PhysHlth ?? defaultProfile.PhysHlth),
            DiffWalk: Number(res.DiffWalk ?? defaultProfile.DiffWalk),
            Sex: Number(res.Sex ?? defaultProfile.Sex),
            Age: Number(res.Age ?? defaultProfile.Age),
            Education: Number(res.Education ?? defaultProfile.Education),
            Income: Number(res.Income ?? defaultProfile.Income),
          });
        }
      } catch (err: any) {
        console.warn('Profile load notice:', err?.message || err);
      } finally {
        setLoading(false);
      }
    };

    loadProfileData();
  }, [user]);

  const handleChange = (key: keyof HealthProfileForm, val: number) => {
    setFormData((prev) => ({ ...prev, [key]: val }));
    setSuccessMsg('');
    setErrorMsg('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSuccessMsg('');
    setErrorMsg('');

    try {
      const payload = {
        HighBP: Number(formData.HighBP),
        HighChol: Number(formData.HighChol),
        CholCheck: Number(formData.CholCheck),
        BMI: Number(formData.BMI),
        Smoker: Number(formData.Smoker),
        Stroke: Number(formData.Stroke),
        HeartDiseaseorAttack: Number(formData.HeartDiseaseorAttack),
        PhysActivity: Number(formData.PhysActivity),
        Fruits: Number(formData.Fruits),
        Veggies: Number(formData.Veggies),
        HvyAlcoholConsump: Number(formData.HvyAlcoholConsump),
        AnyHealthcare: Number(formData.AnyHealthcare),
        NoDocbcCost: Number(formData.NoDocbcCost),
        GenHlth: Number(formData.GenHlth),
        MentHlth: Number(formData.MentHlth),
        PhysHlth: Number(formData.PhysHlth),
        DiffWalk: Number(formData.DiffWalk),
        Sex: Number(formData.Sex),
        Age: Number(formData.Age),
        Education: Number(formData.Education),
        Income: Number(formData.Income),
      };

      await saveProfile(payload);
      setSuccessMsg('Health profile saved successfully.');
    } catch (err: any) {
      console.error('Failed to save profile:', err);
      setErrorMsg(err?.message || 'Failed to save health profile.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <Header
        title="User Profile & Health Status"
        description="Manage your health profile indicators used for preventive risk assessment."
      />

      {loading && <LoadingState message="Loading health profile..." />}

      {!loading && (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Account Info Card */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-900 text-lg font-bold text-white shadow-sm">
                {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">{user?.username || 'Authenticated User'}</h3>
                <p className="text-xs text-slate-500">{user?.email || 'Cognito Account'}</p>
                <div className="mt-1 flex items-center gap-2 text-[11px] font-medium text-slate-600">
                  <Shield className="h-3.5 w-3.5 text-teal-600" />
                  <span>Cognito Subject ID: {user?.userSub || 'Not authenticated'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Feedback Banners */}
          {successMsg && (
            <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs font-semibold text-emerald-700">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {errorMsg && (
            <div className="flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-xs font-semibold text-rose-700">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* 1. Clinical & Medical History */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
              <HeartPulse className="h-5 w-5 text-rose-600" />
              <h3 className="text-sm font-bold text-slate-900">Clinical & Medical History</h3>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700">High Blood Pressure</label>
                <select
                  value={formData.HighBP}
                  onChange={(e) => handleChange('HighBP', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={0}>No (Normal Blood Pressure)</option>
                  <option value={1}>Yes (High BP History)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">High Cholesterol</label>
                <select
                  value={formData.HighChol}
                  onChange={(e) => handleChange('HighChol', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={0}>No (Normal Cholesterol)</option>
                  <option value={1}>Yes (High Cholesterol)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Cholesterol Checked (in 5 yrs)</label>
                <select
                  value={formData.CholCheck}
                  onChange={(e) => handleChange('CholCheck', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={0}>No</option>
                  <option value={1}>Yes</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Body Mass Index (BMI)</label>
                <input
                  type="number"
                  step="0.1"
                  min="10"
                  max="60"
                  value={formData.BMI}
                  onChange={(e) => handleChange('BMI', parseFloat(e.target.value) || 0)}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">History of Stroke</label>
                <select
                  value={formData.Stroke}
                  onChange={(e) => handleChange('Stroke', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={0}>No</option>
                  <option value={1}>Yes</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Heart Disease / Attack</label>
                <select
                  value={formData.HeartDiseaseorAttack}
                  onChange={(e) => handleChange('HeartDiseaseorAttack', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={0}>No</option>
                  <option value={1}>Yes</option>
                </select>
              </div>
            </div>
          </div>

          {/* 2. Lifestyle & Health Behaviors */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
              <Activity className="h-5 w-5 text-teal-600" />
              <h3 className="text-sm font-bold text-slate-900">Lifestyle & Health Behaviors</h3>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700">Smoking History (100+ lifetime)</label>
                <select
                  value={formData.Smoker}
                  onChange={(e) => handleChange('Smoker', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={0}>No</option>
                  <option value={1}>Yes</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Physical Activity (past 30 days)</label>
                <select
                  value={formData.PhysActivity}
                  onChange={(e) => handleChange('PhysActivity', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={0}>No (Inactive)</option>
                  <option value={1}>Yes (Regular Activity)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Fruit Consumption (1+ per day)</label>
                <select
                  value={formData.Fruits}
                  onChange={(e) => handleChange('Fruits', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={0}>No</option>
                  <option value={1}>Yes</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Vegetable Consumption (1+ per day)</label>
                <select
                  value={formData.Veggies}
                  onChange={(e) => handleChange('Veggies', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={0}>No</option>
                  <option value={1}>Yes</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Heavy Alcohol Consumption</label>
                <select
                  value={formData.HvyAlcoholConsump}
                  onChange={(e) => handleChange('HvyAlcoholConsump', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={0}>No</option>
                  <option value={1}>Yes</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Physical Unwell Days (past 30)</label>
                <input
                  type="number"
                  min="0"
                  max="30"
                  value={formData.PhysHlth}
                  onChange={(e) => handleChange('PhysHlth', parseInt(e.target.value, 10) || 0)}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Mental Unwell Days (past 30)</label>
                <input
                  type="number"
                  min="0"
                  max="30"
                  value={formData.MentHlth}
                  onChange={(e) => handleChange('MentHlth', parseInt(e.target.value, 10) || 0)}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* 3. Demographics & General Health */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
              <UserCheck className="h-5 w-5 text-indigo-600" />
              <h3 className="text-sm font-bold text-slate-900">Demographics & Healthcare Access</h3>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700">Biological Sex</label>
                <select
                  value={formData.Sex}
                  onChange={(e) => handleChange('Sex', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={0}>Female</option>
                  <option value={1}>Male</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Age Group</label>
                <select
                  value={formData.Age}
                  onChange={(e) => handleChange('Age', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={1}>18 - 24 years</option>
                  <option value={2}>25 - 29 years</option>
                  <option value={3}>30 - 34 years</option>
                  <option value={4}>35 - 39 years</option>
                  <option value={5}>40 - 44 years</option>
                  <option value={6}>45 - 49 years</option>
                  <option value={7}>50 - 54 years</option>
                  <option value={8}>55 - 59 years</option>
                  <option value={9}>60 - 64 years</option>
                  <option value={10}>65 - 69 years</option>
                  <option value={11}>70 - 74 years</option>
                  <option value={12}>75 - 79 years</option>
                  <option value={13}>80+ years</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">General Health Self-Rating</label>
                <select
                  value={formData.GenHlth}
                  onChange={(e) => handleChange('GenHlth', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={1}>1 - Excellent</option>
                  <option value={2}>2 - Very Good</option>
                  <option value={3}>3 - Good</option>
                  <option value={4}>4 - Fair</option>
                  <option value={5}>5 - Poor</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Difficulty Walking / Stairs</label>
                <select
                  value={formData.DiffWalk}
                  onChange={(e) => handleChange('DiffWalk', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={0}>No</option>
                  <option value={1}>Yes</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Healthcare Coverage</label>
                <select
                  value={formData.AnyHealthcare}
                  onChange={(e) => handleChange('AnyHealthcare', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={0}>Uninsured / No</option>
                  <option value={1}>Covered / Yes</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Doctor Visit Skipped Due to Cost</label>
                <select
                  value={formData.NoDocbcCost}
                  onChange={(e) => handleChange('NoDocbcCost', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={0}>No</option>
                  <option value={1}>Yes</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Education Level</label>
                <select
                  value={formData.Education}
                  onChange={(e) => handleChange('Education', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={1}>Never attended school</option>
                  <option value={2}>Elementary (Grades 1-8)</option>
                  <option value={3}>Some High School (Grades 9-11)</option>
                  <option value={4}>High School Graduate</option>
                  <option value={5}>Some College / Tech School</option>
                  <option value={6}>College Graduate (4+ yrs)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700">Income Bracket</label>
                <select
                  value={formData.Income}
                  onChange={(e) => handleChange('Income', Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none"
                >
                  <option value={1}>Less than $10,000</option>
                  <option value={2}>$10,000 - $15,000</option>
                  <option value={3}>$15,000 - $20,000</option>
                  <option value={4}>$20,000 - $25,000</option>
                  <option value={5}>$25,000 - $35,000</option>
                  <option value={6}>$35,000 - $50,000</option>
                  <option value={7}>$50,000 - $75,000</option>
                  <option value={8}>$75,000 or more</option>
                </select>
              </div>
            </div>
          </div>

          {/* Submit Action Bar */}
          <div className="flex items-center justify-end gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 rounded-lg bg-teal-600 px-5 py-2.5 text-xs font-bold text-white shadow-sm transition-colors hover:bg-teal-700 disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              <span>{saving ? 'Saving Profile...' : 'Save Health Profile'}</span>
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
