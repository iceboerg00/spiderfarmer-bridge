import typescript from '@rollup/plugin-typescript';
import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import terser from '@rollup/plugin-terser';

const isProd = process.env.NODE_ENV === 'production' || !process.env.ROLLUP_WATCH;

export default {
  input: 'src/ggs-card.ts',
  output: {
    file: 'dist/ggs-card.js',
    format: 'es',
    sourcemap: !isProd,
  },
  plugins: [
    resolve(),
    commonjs(),
    typescript({ tsconfig: './tsconfig.json' }),
    isProd && terser({
      format: { comments: false },
      compress: { drop_console: true },
    }),
  ].filter(Boolean),
};
