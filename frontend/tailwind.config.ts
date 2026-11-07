import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        charcoal: {
          50: "#f6f6f7",
          100: "#e1e2e5",
          200: "#c2c4cb",
          300: "#9ea1ac",
          400: "#7c7f8e",
          500: "#636676",
          600: "#4e505e",
          700: "#3e404b",
          800: "#272830",
          900: "#131418",
          950: "#0b0c0f",
        },
        brand: {
          orange: "#FF5E1E",
          hover: "#E04E15",
          light: "#FFF1EB",
        },
      },
    },
  },
  plugins: [],
};
export default config;
