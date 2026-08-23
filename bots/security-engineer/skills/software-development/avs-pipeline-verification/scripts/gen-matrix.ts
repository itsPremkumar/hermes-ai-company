// gen-matrix.ts — emits a full combinatorial agentic-scripts.json for AVS verification.
// Run: npx tsx scripts/gen-matrix.ts   (from repo root). Backs up current script first.
import * as fs from 'fs';

const ASSETS = ['github-profile.png', 'logo-automation.png'];
const MUSIC = ['lofi_chill.mp3', 'cinematic_drone.mp3', 'upbeat_electronic.mp3', 'ambient_piano.mp3', 'ambient_nature.mp3'];
const ORIENTS = ['portrait', 'landscape', 'square'];
const CAPTIONS = ['burned', 'karaoke', 'none'];
const VOICES: Record<string, string> = {
  'en-US-GuyNeural': 'english', 'en-GB-RyanNeural': 'english', 'en-IN-NeerjaNeural': 'english',
  'es-ES-AlvaroNeural': 'spanish', 'hi-IN-SwararaNeural': 'hindi', 'ta-IN-PallaviNeural': 'tamil',
  'fr-FR-DeniseNeural': 'french', 'de-DE-KatjaNeural': 'german',
};
const GRADES = ['neutral', 'warm', 'cool', 'cinematic', 'vivid'];
const TRANSITIONS = ['fade', 'slide', 'zoomblur', 'cut'];
const STYLES = ['top', 'bottom', 'center'];
const COLORS = ['white', 'yellow'];
const CAP_THEMES = ['neon', 'bold', 'minimal'];
const MUSIC_INTENSITY = ['calm', 'mid', 'energetic'];

const jobs: any[] = [];
let n = 0;
const id = (p: string) => `combo_${String(++n).padStart(3, '0')}_${p}`;

// Tier 1: orientation x captions x {music, nomusic}
for (const o of ORIENTS) for (const c of CAPTIONS) for (const m of [0, 1]) {
  const music = m ? MUSIC[(ORIENTS.indexOf(o) + CAPTIONS.indexOf(c)) % MUSIC.length] : '';
  jobs.push({
    id: id(`render_${o}_${c}_${m ? 'mus' : 'nomus'}`),
    title: `Render ${o} ${c} ${m ? 'music' : 'nomusic'}`,
    topic: 'combinatorial test',
    script: `First scene of the test. [Visual: ${ASSETS[0]}] [Grade: ${GRADES[n % GRADES.length]}] [Transition: ${TRANSITIONS[n % TRANSITIONS.length]}]\nSecond scene continues. [Visual: ${ASSETS[1]}] [Style: ${STYLES[n % STYLES.length]}] [Color: ${COLORS[n % COLORS.length]}] [FadeIn: 0.3] [FadeOut: 0.3]`,
    orientation: o, voice: 'en-US-GuyNeural', language: 'english', backend: 'heuristic', candidatesPerAsset: 1,
    captions: c, captionTheme: CAP_THEMES[n % CAP_THEMES.length], vignette: n % 2 === 0, kineticText: n % 2 === 1,
    sfx: n % 3 !== 0, musicIntensity: MUSIC_INTENSITY[n % MUSIC_INTENSITY.length], jCutSec: 0.2,
    preset: o === 'portrait' ? 'reels' : o === 'landscape' ? 'cinematic' : 'square', localAssets: ASSETS,
    ...(music ? { backgroundMusic: music, musicVolume: 0.15 } : {}),
  });
}
// Tier 2: every voice/language
let vi = 0;
for (const [v, lang] of Object.entries(VOICES)) jobs.push({
  id: id(`voice_${v}`), title: `Voice ${v}`, topic: 'voice test',
  script: `This is the ${lang} voice test. [Visual: ${ASSETS[0]}] [Grade: warm]\nSpeaking clearly for verification. [Visual: ${ASSETS[1]}] [Kinetic: on] [CaptionTheme: neon]`,
  orientation: 'portrait', voice: v, language: lang, backend: 'heuristic', candidatesPerAsset: 1,
  captions: 'burned', captionTheme: 'neon', vignette: true, kineticText: true, sfx: true, musicIntensity: 'calm',
  preset: 'reels', localAssets: ASSETS, backgroundMusic: MUSIC[vi++ % MUSIC.length], musicVolume: 0.15,
});
// Tier 3: inline-tag enum coverage
GRADES.forEach((g, i) => jobs.push({ id: id(`grade_${g}`), title: `Grade ${g}`, topic: 'g',
  script: `Grade test ${g}. [Visual: ${ASSETS[i % 2]}] [Grade: ${g}]\nSecond grade scene. [Visual: ${ASSETS[(i + 1) % 2]}] [Grade: ${g}] [Transition: slide]`,
  orientation: 'portrait', voice: 'en-US-GuyNeural', language: 'english', backend: 'heuristic', candidatesPerAsset: 1,
  captions: 'burned', captionTheme: 'bold', vignette: true, kineticText: true, sfx: false, musicIntensity: 'mid', preset: 'reels', localAssets: ASSETS, backgroundMusic: MUSIC[i % MUSIC.length], musicVolume: 0.15 }));
TRANSITIONS.forEach((t, i) => jobs.push({ id: id(`trans_${t}`), title: `Transition ${t}`, topic: 't',
  script: `Transition test ${t}. [Visual: ${ASSETS[i % 2]}] [Transition: ${t}] [KenBurns: on]\nSecond transition. [Visual: ${ASSETS[(i + 1) % 2]}] [Transition: ${t}] [Trim: 0:00-0:04]`,
  orientation: 'landscape', voice: 'en-US-GuyNeural', language: 'english', backend: 'heuristic', candidatesPerAsset: 1,
  captions: 'karaoke', captionTheme: 'minimal', vignette: false, kineticText: false, sfx: true, musicIntensity: 'energetic', preset: 'cinematic', localAssets: ASSETS, backgroundMusic: MUSIC[i % MUSIC.length], musicVolume: 0.15 }));
STYLES.forEach((s, i) => jobs.push({ id: id(`style_${s}`), title: `Style ${s}`, topic: 's',
  script: `Style test ${s}. [Visual: ${ASSETS[i % 2]}] [Style: ${s}] [Color: ${COLORS[i % COLORS.length]}]\nSecond style. [Visual: ${ASSETS[(i + 1) % 2]}] [Style: ${s}] [Color: ${COLORS[(i + 1) % COLORS.length]}]`,
  orientation: 'square', voice: 'en-US-GuyNeural', language: 'english', backend: 'heuristic', candidatesPerAsset: 1,
  captions: 'burned', captionTheme: 'neon', vignette: true, kineticText: true, sfx: false, musicIntensity: 'calm', preset: 'square', localAssets: ASSETS, backgroundMusic: MUSIC[i % MUSIC.length], musicVolume: 0.15 }));
jobs.push({ id: id(`tags_full`), title: 'All Inline Tags', topic: 'full',
  script: `Caption neon and calm music. [Visual: ${ASSETS[0]}] [CaptionTheme: neon] [MusicIntensity: calm] [Sfx: on] [JCut: 0.3] [Vignette: on] [Kinetic: on]\nCaption bold and energetic. [Visual: ${ASSETS[1]}] [CaptionTheme: bold] [MusicIntensity: energetic] [Sfx: off] [Vignette: off] [Kinetic: off] [Trim: 0:00-0:04]`,
  orientation: 'portrait', voice: 'en-US-GuyNeural', language: 'english', backend: 'heuristic', candidatesPerAsset: 1,
  captions: 'burned', captionTheme: 'neon', vignette: true, kineticText: true, sfx: true, musicIntensity: 'calm', jCutSec: 0.3, preset: 'reels', localAssets: ASSETS, backgroundMusic: MUSIC[0], musicVolume: 0.15 });
// Tier 4: control-surface dryRun (all 19 inline tags + top-level config reachability)
jobs.push({ id: id(`controlsurface_dry`), title: 'Control Surface Dry', topic: 'cs',
  script: `Control surface dry run. [Visual: ${ASSETS[0]}] [Grade: warm] [Transition: zoomblur] [KenBurns: on] [CaptionTheme: neon] [Kinetic: on] [JCut: 0.2] [Vignette: on] [Sfx: off] [MusicIntensity: energetic] [Style: center] [Color: yellow] [FadeIn: 0.4] [FadeOut: 0.4] [Trim: 0:00-0:04] [Voice: en-GB-RyanNeural] [Music: lofi_chill.mp3] [Volume: 0.8]\nSecond scene all tags. [Visual: ${ASSETS[1]}] [Grade: vivid] [Transition: slide] [CaptionTheme: bold] [Kinetic: off] [Vignette: off] [Sfx: on] [MusicIntensity: mid] [Style: top] [Color: white]`,
  orientation: 'portrait', voice: 'en-US-GuyNeural', language: 'english', backend: 'heuristic', candidatesPerAsset: 1,
  captions: 'burned', captionTheme: 'neon', vignette: true, kineticText: true, jCutSec: 0.2, musicIntensity: 'energetic', sfx: false, preset: 'reels', platform: 'instagram', videoType: 'reel', brand: 'AVS', hookFirst: true, variablePacing: true,
  aiVerify: { enabled: true, checkSubjectMatch: true, finalMode: 'vision' }, brain: { maxCalls: 5, maxFails: 2 }, pruneWorkspaces: 4, dryRun: true, defaultVisual: ASSETS[0], agent: {}, localAssets: ASSETS, backgroundMusic: MUSIC[0], musicVolume: 0.15 });

fs.copyFileSync('input/scripts/agentic-scripts.json', 'input/scripts/agentic-scripts.json.bak');
fs.writeFileSync('input/scripts/agentic-scripts.json', JSON.stringify(jobs, null, 2));
console.log(`Generated ${jobs.length} jobs (Tier1 render + Tier2 voices + Tier3 tags + Tier4 dryRun).`);
console.log('Run: npx tsx src/adapters/cli/agentic-cli.ts  (background, ~30-60s/job)');
