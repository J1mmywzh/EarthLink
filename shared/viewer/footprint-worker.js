importScripts('./footprints.js');
self.onmessage=event=>{try{self.postMessage({polygons:EarthLinkFootprints.derive(event.data)});}catch(error){self.postMessage({error:error.message});}};
