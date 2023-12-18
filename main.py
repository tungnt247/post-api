# """Post api"""
import os
import uuid
import boto3
from dotenv import load_dotenv
from flask import Flask, request, abort
from flask_restful import reqparse, abort, Api, Resource


load_dotenv()
app = Flask(__name__)
api = Api(app)
dynamodb = boto3.client('dynamodb',
                    region_name=os.getenv('APP_REGION'),
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))
s3 = boto3.client('s3',
                    region_name=os.getenv('APP_REGION'),
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

@app.route("/")
def health_check():
    """server health check
    Returns:
        _type_: json
    """
    return {'message': 'oklaaaa'}

def upload_images(images, post_id):
    urls = []
    for image in images:
        if image.filename == '':
            continue

        try:
            key = f'{post_id}/{image.filename}'
            bucket = os.getenv('S3_BUCKET')
            s3.put_object(
                Body=image,
                Bucket=bucket,
                Key=key,
                ContentType=image.mimetype
            )
            urls.append(f'https://{bucket}.s3-ap-southeast-1.amazonaws.com/{key}')
        except Exception as e:
            print(e)
    return urls

def delete_images(post_id):
    res = s3.list_objects(Bucket=os.getenv('S3_BUCKET'), Prefix=post_id)
    deleting_keys = {'Objects': []}
    deleting_keys['Objects'] = [{'Key' : k} for k in [obj['Key'] for obj in res.get('Contents', [])]]
    s3.delete_objects(Bucket=os.environ('S3_BUCKET'), Delete=deleting_keys)


class RetriveUpdateDestroyPost(Resource):
    def get(self, post_id):
        return self._get_post(post_id=post_id)

    def delete(self, post_id):
        post = self._get_post(post_id=post_id)
        if post['images']['L']:
            delete_images(post_id=post_id)

        dynamodb.delete_item(
            TableName='posts',
            Key={'id': {'S': post_id}}
        )
        return '', 204

    def put(self, post_id):
        self._set_post_params()
        post = self._get_post(post_id=post_id)
        params = request.form.to_dict()
        updating_data = []
        expression_attribute_values = {}

        for k, v in params.items():
            expression_attribute_value_key = f':{k}'
            updating_data.append(f'{k} = :{k}')
            expression_attribute_values[expression_attribute_value_key] = {'S': v}

        if params.get('update_images'):
            if post['images']['L']:
                delete_images(post_id=post_id)

            updating_data.append('images = :images')
            expression_attribute_values[':images'] = {'L': []}
            images = request.files.getlist('images')

            if images:
                updating_urls = upload_images(images=images, post_id=post_id)
                image_urls = [{'S': image} for image in updating_urls]
                expression_attribute_values[':images'] = {'L': image_urls}


        res = dynamodb.update_item(
            TableName='posts',
            Key={'id': {'S': post_id}},
            UpdateExpression='SET' + ' ' + (', ').join(updating_data),
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues='ALL_NEW'
        )
        return res['Attributes']

    def _get_post(self, post_id):
        res = dynamodb.get_item(
            TableName='posts',
            Key={'id': {'S': post_id}}
        )
        if res.get('Item'):
            return res['Item']
        else:
            abort(404, message=f'Post with id {post_id} is not exist')

    def _set_post_params(self):
        parser = reqparse.RequestParser()
        parser.add_argument('title', type=str, required=False, location='form')
        parser.add_argument('content', type=str, required=False, location='form')
        parser.add_argument('images', type=str, required=False, location='form')
        parser.add_argument('update_images', type=bool, required=False, default=False, location='form')

class ListCreatePost(Resource):
    def get(self):
        response = dynamodb.scan(TableName='posts')
        data = response['Items']
        return data

    def post(self):
        self._set_post_params()
        data = request.form.to_dict()
        data['id'] = uuid.uuid4().hex
        images = request.files.getlist('images')
        image_urls = upload_images(images=images, post_id=data['id'])
        data['images'] = image_urls
        post = self._create_new_post(post=data)
        return post, 201

    def _create_new_post(self, post):
        try:
            item = {
                'id': {'S': post['id']},
                'title': {'S': post['title']},
                'content': {'S': post['content']}
            }

            if post.get('images'):
                urls = [{'S': image} for image in post['images']]
                item['images'] = {'L': urls}
            else:
                item['images'] = {'L': []}

            dynamodb.put_item(
                TableName='posts',
                Item=item
            )
            return post
        except Exception as e:
            print(e)

    def _set_post_params(self):
        parser = reqparse.RequestParser()
        parser.add_argument('title', type=str, required=True, location='form')
        parser.add_argument('content', type=str, required=True, location='form')
        parser.add_argument('images', type=str, required=False, location='form')

api.add_resource(ListCreatePost, '/api/v1/posts')
api.add_resource(RetriveUpdateDestroyPost, '/api/v1/posts/<post_id>')


if __name__ == '__main__':
    app.run(debug=True)
