importScripts('./footprints.js');
self.onmessage=event=>{try{self.postMessage(EarthLinkFootprints.deriveAll(event.data.mesh,event.data.margin));}catch(error){self.postMessage({error:error.message});}};
