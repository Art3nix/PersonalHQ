/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./personalhq/templates/**/*.html",
    "./personalhq/static/**/*.js",
  ],
  safelist: [
    // Trimmed: Removed 'shadow', 'from', 'to' unless you specifically use dynamic gradients.
    // Trimmed: Removed 'group-hover' and 'peer-checked' variants.
    {
      pattern: /^(bg|text|border|ring)-(stone|red|orange|amber|yellow|lime|emerald|teal|cyan|sky|blue|indigo|violet|fuchsia|rose)-(50|100|200|300|400|500|600|700|800|900)/,
      variants: ['hover'], 
    },
    // Trimmed: Only generate opacities for background colors on a few mid-range shades
    // (Usually, dynamic UI backgrounds only use /10 or /20 opacities)
    {
      pattern: /^bg-(stone|red|orange|amber|yellow|lime|emerald|teal|cyan|sky|blue|indigo|violet|fuchsia|rose)-(500|600)\/(10|20)/,
    }
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
