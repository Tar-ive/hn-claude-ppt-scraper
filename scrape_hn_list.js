() => {
  var items = Array.from(document.querySelectorAll('.athing'), el => {
    const title = el.querySelector('.titleline a').innerText;
    const pointsEl = el.nextSibling.querySelector('.score');
    const points = pointsEl ? parseInt(pointsEl.innerText) : 0;
    const url = el.querySelector('.titleline a').href;
    const dt = el.nextSibling.querySelector('.age')?.title?.split(' ')[0] || null;
    const submitter = el.nextSibling.querySelector('.hnuser')?.innerText || null;
    const commentsUrl = el.nextSibling.querySelector('.age a')?.href || null;
    const id = commentsUrl ? commentsUrl.split('?id=')[1] : el.id?.replace('thing_', '');
    // Only posts with comments have a comments link
    const commentsLink = Array.from(
      el.nextSibling.querySelectorAll('a')
    ).filter(el => el && el.innerText.includes('comment'))[0];
    let numComments = 0;
    if (commentsLink) {
      numComments = parseInt(commentsLink.innerText.split()[0]);
    }
    return {id, title, url, dt, points, submitter, commentsUrl, numComments};
  });
  if (!items.length) {
    throw 'No items found';
  }
  return items;
}
