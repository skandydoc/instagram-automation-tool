import os
import requests
import time

access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
ig_user_id = '17841475613013338'
image_url = 'https://storage.googleapis.com/instagram-automation-storage-studylog/quote_02.png'
caption = 'The ECG never lies—neither should your work ethic.\n\nFollow @MBBS_Motivation_Mafia for more inspiration!'

# Step 1: Create image container
container_url = f'https://graph.facebook.com/v19.0/{ig_user_id}/media'
container_payload = {
    'image_url': image_url,
    'caption': caption,
    'access_token': access_token
}
resp1 = requests.post(container_url, data=container_payload)
print('Container response:', resp1.status_code, resp1.text)

container_id = None
try:
    container_id = resp1.json().get('id')
except Exception as e:
    print('Error parsing container response:', e)

if container_id:
    # Step 2: Poll for container status
    status_url = f'https://graph.facebook.com/v19.0/{container_id}'
    status = None
    for attempt in range(10):
        resp_status = requests.get(status_url, params={'fields': 'status_code', 'access_token': access_token})
        try:
            status = resp_status.json().get('status_code')
        except Exception as e:
            print(f'Error parsing status response on attempt {attempt+1}:', e)
        print(f'Attempt {attempt+1}: Container status:', resp_status.status_code, resp_status.text)
        if status == 'FINISHED':
            print('Container is ready to be published.')
            break
        elif status == 'ERROR' or status == 'EXPIRED':
            print('Container processing failed or expired.')
            break
        time.sleep(5)
    else:
        print('Container was not ready after polling. Exiting.')
        exit(1)
    if status == 'FINISHED':
        # Step 3: Publish the image
        publish_url = f'https://graph.facebook.com/v19.0/{ig_user_id}/media_publish'
        publish_payload = {
            'creation_id': container_id,
            'access_token': access_token
        }
        resp2 = requests.post(publish_url, data=publish_payload)
        print('Publish response:', resp2.status_code, resp2.text)
    else:
        print('Container was not ready for publishing.')
else:
    print('No container created, skipping publish.') 