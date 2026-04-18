import { Suspense } from 'react';
import LoginContent from '@/components/login-content';

function LoadingLogin() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas">
      <div className="h-96 w-96 animate-pulse rounded-lg border border-edge bg-canvas-raised" />
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoadingLogin />}>
      <LoginContent />
    </Suspense>
  );
}
