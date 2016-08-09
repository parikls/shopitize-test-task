## Twitter Album creator

Creates albums with photos based on provided `hashtag`
Developed with `python 3.5` and `Django 1.9`

#### Quick start

1. Install requirements `pip install -r requirements.txt`
2. Create database `python manage.py migrate`
3. Run tests `python manage.py test`
4. Run development server `python manage.py runserver`


#### API

**Resources**
- album


**Endpoints**
- /api/album/
- /api/album/pk/


**Available methods**
- /api/album/ : `GET`, `POST`
- /api/album/pk/: `GET`, `PATCH`

**Sample Requests**


`GET /api/album/`

*Example response*

Code: `200`

    `{"message": null,
      "data": [
        {
          "pk": 1,
          "hashtag": "#hashtag",
          "images": [
            {
              "media_url": "http://image1.media.url.com",
              "url": "http://image1.media.url.com",
              "twitter_id": 1
            },
            {
              "media_url": "http://image2.media.url.com",
              "url": "http://image2.media.url.com",
              "twitter_id": 2
            }
          ]
        },
        {
          "pk": 2,
          "hashtag": "#hashtag2",
          "images": [
            {
              "media_url": "http://image3.media.url.com",
              "url": "http://image3.media.url.com",
              "twitter_id": 3
            }
          ]
        },
      ]
    }`


`GET /api/album/1/`

*Example response*

Code: `200`

    `{"message": null,
      "data": 
        {
          "pk": 1,
          "hashtag": "#hashtag",
          "preview_image": 
            {
              "media_url": "http://image.media.url.com",
              "url": "http://image.url.com",
              "twitter_id": 1
            },
          "images": [
            {
              "media_url": "http://image.media.url.com",
              "url": "http://image.media.url.com",
              "twitter_id": 1
            }
          ]
        }
      }`


`POST /api/album/`
`Params`: hashtag=#hashtag
*Request must contain `CSRF` token*

*Example response*

Code: `201`
Additional headers: `Location`=`http://host/api/album/1/`

    `{"message": "Successfully created new album for hashtag #hashtag",
      "data": {
          "pk": 1,
          "hashtag": "#hashtag",
          "images": [
              {
                  "media_url": "http://image.media.url.com",
                  "url": "http://image.media.url.com",
                  "twitter_id": 1
              }
          ]
      }}`


`PATCH /api/album/1/`
*Request must contain `CSRF` token*

*Example response*

Code: `200`

    `{"message": "Successfully updated album with hashtag #hashtag",
      "data": {
        "pk": 1,
        "hashtag": "#hashtag",
        "images": [
          {
            "media_url": "http://image.media.url.com",
            "url": "http://image.media.url.com",
            "twitter_id": 1
          }
        ]
      }
    }`


`PATCH /api/album/1/`
*Request must contain `CSRF` token*

*Example response*

Code: `200`

    `{
      "message": "No new images",
      "data": null
      }`


**Error codes**

  1. Sending an invalid `POST` request will result in `400 Bad Request` status :
  
        `HTTP/1.1 400 Bad Request
        {"message": Parameter hashtag was not found in request"}`
   
  2. Sending `GET` request on nonexistent resource will result in `404 Not Found`:
  
        `HTTP/1.1 404 Not Found
        {"message": "No such album"}`
   
  3. Sending `POST` or `PATCH` request, which creates or changing resource could result in 
        `500 Internal Server Error` if server could not download image from external resource
        
        `HTTP/1.1 500 Internal Server Error
        {"message": "Error occurred while downloading photo =("}`
        
  4. Sending `POST` or `PATCH` request, which creates or changing resource could result in 
        `503 Service Unavailable` when there is no respond from Twitter
        
        `HTTP/1.1 503 Service Unavailable
        {"message": "Could not obtain data from Twitter"}`
