/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./personalhq/templates/**/*.html",
    "./personalhq/static/**/*.js",
  ],
  // Safelist dynamic color classes used via Jinja (e.g. bg-{{ theme }}-50)
  safelist: [
    {
      pattern: /^(bg|text|border|ring|shadow|from|to)-(stone|red|orange|amber|yellow|lime|emerald|teal|cyan|sky|blue|indigo|violet|fuchsia|rose)-(50|100|200|300|400|500|600|700|800|900|950)/,
      variants: ['hover', 'group-hover', 'peer-checked'],
    },
    {
      pattern: /^(bg|text|border|shadow)-(stone|red|orange|amber|yellow|lime|emerald|teal|cyan|sky|blue|indigo|violet|fuchsia|rose)-(50|100|200|300|400|500|600|700|800|900)\/(10|20|30|40|50|60|70|80)/,
    },
    {
      pattern: /^ring-(stone|red|orange|amber|yellow|lime|emerald|teal|cyan|sky|blue|indigo|violet|fuchsia|rose)-(100|200|300|400|500|600|700|800)/,
    },
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
