/**
 * Factory selection page.
 * Users select their factory before logging in.
 */
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { auth } from '../api/endpoints';
import type { Factory } from '../types';

export default function FactorySelectPage() {
  const navigate = useNavigate();

  const { data: factories, isLoading, error } = useQuery({
    queryKey: ['factories'],
    queryFn: auth.getFactories,
  });

  const handleFactorySelect = (factory: Factory) => {
    // Store selected factory in sessionStorage
    sessionStorage.setItem('selectedFactory', JSON.stringify(factory));
    
    // Redirect to login with factory_id
    navigate(`/login?factory_id=${factory.id}`);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading factories...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 mb-4">
            <svg className="h-12 w-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Failed to load factories</h2>
          <p className="text-gray-600">Please try again later.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="max-w-4xl w-full">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">FactoryOps</h1>
          <p className="text-gray-600">Select your factory to continue</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {factories?.map((factory) => (
            <button
              key={factory.id}
              onClick={() => handleFactorySelect(factory)}
              className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow text-left border-2 border-transparent hover:border-blue-500"
            >
              <h2 className="text-xl font-semibold text-gray-900 mb-2">{factory.name}</h2>
              <p className="text-sm text-gray-500">Slug: {factory.slug}</p>
            </button>
          ))}
        </div>

        {factories?.length === 0 && (
          <div className="text-center text-gray-600 mt-8">
            <p>No factories available</p>
          </div>
        )}
      </div>
    </div>
  );
}
