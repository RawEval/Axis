import { Suspense } from 'react';
import LoginContent from '@/components/login-content';

export default function LoginPage() {
  return (
    <Suspense>
      <LoginContent />
    </Suspense>
  );
}
