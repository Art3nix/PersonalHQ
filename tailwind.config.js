/** @type {import('tailwindcss').Config} */

// 1. Define your parameters
const colors = ['stone', 'red', 'orange', 'amber', 'yellow', 'lime', 'emerald', 'teal', 'cyan', 'sky', 'blue', 'indigo', 'violet', 'fuchsia', 'rose'];
const prefixes = ['bg', 'text', 'border', 'ring'];
const shades = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900'];

// 2. Pre-compute the exact list of strings
const mySafelist = [];

colors.forEach(color => {
  // Generate the main color classes
  shades.forEach(shade => {
    prefixes.forEach(prefix => {
      mySafelist.push(`${prefix}-${color}-${shade}`);
      mySafelist.push(`hover:${prefix}-${color}-${shade}`); // Explicitly add the hover variant
    });
  });
  
  // Generate the specific opacity backgrounds
  ['500', '600'].forEach(shade => {
    mySafelist.push(`bg-${color}-${shade}/10`);
    mySafelist.push(`bg-${color}-${shade}/20`);
  });
});

module.exports = {
  content: [
    "./personalhq/templates/**/*.html",
    "./personalhq/static/**/*.js",
  ],
  // 3. Feed the exact array to Tailwind
  safelist: mySafelist,
  theme: {
    extend: {},
  },
  plugins: [],
}
