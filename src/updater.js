// Автообновление APK через GitHub Releases
// Проверяет новую версию и качает без ручной рассылки

export async function checkForUpdate(currentVersion = "1.0.0") {
  try {
    const repo = localStorage.getItem('githubRepo') || 'heckar904-cmyk/my-agent';
    // GitHub API - последний релиз
    const res = await fetch(`https://api.github.com/repos/${repo}/releases/latest`);
    if(!res.ok) return null;
    const data = await res.json();
    const latest = data.tag_name?.replace('v','') || "1.0.0";
    
    if(latest !== currentVersion) {
      return {
        hasUpdate: true,
        version: latest,
        notes: data.body || "Новая версия",
        apkUrl: data.assets?.[0]?.browser_download_url || `https://github.com/${repo}/releases/latest/download/app-debug.apk`,
        published: data.published_at
      };
    }
    return {hasUpdate: false, version: currentVersion};
  } catch(e) {
    console.log('Update check failed', e);
    return null;
  }
}

export async function downloadUpdate(apkUrl) {
  // В PWA - открываем ссылку, в APK - скачиваем через Filesystem
  window.open(apkUrl, '_blank');
}
