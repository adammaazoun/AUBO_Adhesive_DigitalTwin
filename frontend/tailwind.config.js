/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--color-background)',
        foreground: 'var(--color-foreground)',
        primary: 'var(--color-primary)',
        secondary: 'var(--color-secondary)',
        destructive: 'var(--color-destructive)',
        success: 'var(--color-success)',
        warning: 'var(--color-warning)',
        muted: 'var(--color-muted)',
        border: 'var(--color-border)',
        input: 'var(--color-input)',
      },
      borderRadius: {
        md: 'var(--radius)',
      },
    },
  },
  plugins: [],
}
