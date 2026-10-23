// Párování ověřených IČO se smlouvami města v registru smluv.
// Spouští se v konzoli prohlížeče na https://smlouvy.gov.cz/vyhledavani (stránka s výsledky libovolného
// hledání, aby existoval odkaz "500" se všemi parametry formuláře). Server registru smluv blokuje
// přímý přístup z cloudového sandboxu, proto běh v prohlížeči.
// Vstup: pole ICO (z data/entity/ares_overeni.json bez 00304450). Výstup: window._sum (souhrn dle IČO).
// Pro každé IČO: A = publikující 00304450 + smluvní strana IČO; B = publikující IČO + smluvní strana 00304450.
const MESTO = '00304450';
async function parovani(ICO) {
  const base = [...document.querySelectorAll('a')].find(a => a.innerText.trim() === '500').getAttribute('href');
  const mk = (sub, par) => { const u = new URL(base, location.href); u.searchParams.set('subject_idnum', sub); u.searchParams.set('party_idnum', par); return u.pathname + u.search; };
  const parse = html => {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const cnt = (doc.body.textContent.match(/Počet nalezných záznámů\s*(\d+)/) || [])[1];
    const rows = [...doc.querySelectorAll('table tbody tr')].map(tr => {
      const t = [...tr.querySelectorAll('td')].map(td => td.textContent.trim().replace(/\s+/g, ' '));
      const a = tr.querySelector('a[href^="/smlouva/"]');
      return { pub: t[0], predmet: t[1], posledni: t[2], zverejneno: t[3], hodnota: t[4], strany: t[5], id_verze: a ? a.getAttribute('href').match(/\/smlouva\/(\d+)/)[1] : null };
    });
    return { pocet: cnt ? +cnt : 0, rows };
  };
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const get = async url => { for (let i = 0; i < 3; i++) { try { const r = await fetch(url); if (r.ok) return parse(await r.text()); } catch (e) {} await sleep(3000); } return null; };
  const res = {}, rev = {};
  for (const ico of ICO) { res[ico] = await get(mk(MESTO, ico)); await sleep(1200); rev[ico] = await get(mk(ico, MESTO)); await sleep(1200); }
  const val = s => { const m = (s || '').match(/^(-?[\d ]+)\s*CZK\s*(bez DPH|s DPH)/); return m ? { v: +m[1].replace(/ /g, ''), k: m[2] === 'bez DPH' ? 'b' : 's' } : null; };
  const dt = s => s.split('.').reverse().join('-');
  const sum = {};
  for (const ico of ICO) {
    const all = [...res[ico].rows, ...rev[ico].rows]; if (!all.length) continue;
    const own = all.filter(r => r.strany !== 'Více smluvních stran');
    let sb = 0, ss = 0, nv = 0; own.forEach(r => { const x = val(r.hodnota); if (!x) { nv++; return; } x.k === 'b' ? sb += x.v : ss += x.v; });
    const ds = own.map(r => dt(r.zverejneno)).sort();
    const dod = own.filter(r => /dodatek/i.test(r.predmet));
    sum[ico] = { n: own.length, n_vice_stran: all.length - own.length, pub_protistrana: rev[ico].rows.length, bez_dph: sb, s_dph: ss, bez_hodnoty: nv,
      od: ds[0], do: ds[ds.length - 1], dodatky: dod.length, dodatky_cena: dod.filter(r => /cen|víceprác/i.test(r.predmet)).length,
      dary: own.filter(r => /DARY|darovac/i.test(r.predmet)).map(r => [r.id_verze, dt(r.zverejneno), r.hodnota]),
      top: own.map(r => ({ r, x: val(r.hodnota) })).filter(e => e.x).sort((a, b) => b.x.v - a.x.v).slice(0, 3).map(e => [e.r.id_verze, dt(e.r.zverejneno), e.x.v, e.x.k]) };
  }
  window._sum = sum; return sum;
}
