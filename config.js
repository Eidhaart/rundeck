const RUNDECK_PUBLIC_CONFIG={
  supabaseUrl:"https://mdfdzrncuznuxbavvsrz.supabase.co",
  supabaseAnonKey:"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1kZmR6cm5jdXpudXhiYXZ2c3J6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTIyNTY5NDEsImV4cCI6MjEwNzgzMjk0MX0.Wd_8eC9yJ7kTOcNgH3v3OkciRYDvf6O0wpCuuMYcvro",
  turnstileSiteKey:"0x4AAAAAAFZgN4nZIwuZ-V7X"
};

// The anon key is public by design; share only this configuration with the read-only widget proxy.
if (typeof window !== 'undefined') window.RUNDECK_CONFIG = RUNDECK_PUBLIC_CONFIG;
if (typeof module !== 'undefined' && module.exports) module.exports = RUNDECK_PUBLIC_CONFIG;
